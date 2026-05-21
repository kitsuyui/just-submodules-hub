from __future__ import annotations

import dataclasses
import io
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

import just_submodules_hub.linked_worktree_apply as apply_sync


def record(action: str, target: str = "origin/main") -> Any:
    return apply_sync.PlanRecord(
        path="/repo",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="planned",
        action=action,
        target=target,
        message="planned",
    )


def completed(
    args: list[str],
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def test_apply_plan_leaves_skipped_records_unchanged() -> None:
    skipped = apply_sync.PlanRecord(
        "/repo",
        "feature/test",
        "dirty",
        "",
        "",
        "skipped",
        "skip-dirty",
        "",
        "dirty",
    )

    assert apply_sync.apply_plan(skipped) == skipped


def test_apply_plan_fast_forwards_default_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[Path, list[str]]] = []
    heads = iter(["before", "after"])

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append((repo, args))
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout=f"{next(heads)}\n")
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    assert apply_sync.apply_plan(record("pull-default")) == apply_sync.PlanRecord(
        path="/repo",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="updated",
        action="pull-default",
        target="origin/main",
        message="fast-forwarded",
    )
    assert calls == [
        (Path("/repo"), ["rev-parse", "HEAD"]),
        (Path("/repo"), ["fetch", "origin", "main"]),
        (Path("/repo"), ["merge", "--ff-only", "origin/main"]),
        (Path("/repo"), ["rev-parse", "HEAD"]),
    ]


def test_apply_plan_retires_branch_by_resetting_to_target(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout="same\n")
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("retire-contained"))

    assert result.status == "settled"
    assert result.message == "branch reset to origin/main"
    assert calls == [
        ["rev-parse", "HEAD"],
        ["fetch", "origin", "main"],
        ["switch", "-C", "feature/test", "origin/main"],
        ["rev-parse", "HEAD"],
    ]


def test_apply_plan_rebases_branch_without_force_push(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout="before\n" if len(calls) == 1 else "after\n")
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("rebase-branch", "origin/feature/test"))

    assert result.status == "updated"
    assert result.message == "rebased onto origin/feature/test"
    assert calls == [
        ["rev-parse", "HEAD"],
        ["fetch", "origin", "feature/test"],
        ["rebase", "origin/feature/test"],
        ["rev-parse", "HEAD"],
    ]


def test_apply_plan_aborts_rebase_on_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A failing rebase must run ``git rebase --abort`` and note that.

    Without the abort, the worktree is left in REBASING state with
    conflict markers, blocking subsequent runs and surprising users
    who only see a ``failed`` row in the report.
    """
    calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout="before\n")
        if args == ["rebase", "origin/main"]:
            return completed(args, stderr="CONFLICT (content)", returncode=1)
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("rebase-default", "origin/main"))

    assert result.status == "failed"
    assert "CONFLICT" in result.message
    assert result.message.endswith("; rebase aborted")
    assert ["rebase", "--abort"] in calls


def test_apply_plan_omits_aborted_suffix_when_abort_also_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If ``git rebase --abort`` itself fails, do not claim it succeeded.

    The message must still tell the user that --abort failed and that the
    worktree may remain in REBASING state so they know manual cleanup is needed.
    """
    calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout="before\n")
        if args == ["rebase", "origin/main"]:
            return completed(args, stderr="CONFLICT (content)", returncode=1)
        if args == ["rebase", "--abort"]:
            return completed(args, stderr="abort failed", returncode=1)
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("rebase-default", "origin/main"))

    assert result.status == "failed"
    assert "CONFLICT" in result.message
    assert "rebase aborted" not in result.message
    assert "rebase --abort also failed" in result.message
    assert "REBASING" in result.message
    assert ["rebase", "--abort"] in calls


def test_apply_plan_reports_git_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["fetch", "origin", "main"]:
            return completed(args, stderr="fetch failed", returncode=1)
        return completed(args, stdout="before\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("pull-default"))

    assert result.status == "failed"
    assert result.message == "fetch failed"


# ---------------------------------------------------------------------------
# Tests for --from-plan-stdin / read_plan_from_stdin
# ---------------------------------------------------------------------------


def _make_plan_record(**overrides: str) -> Any:
    """Return a PlanRecord with sensible defaults; fields can be overridden."""
    defaults: dict[str, str] = {
        "path": "/repo",
        "branch": "feature/test",
        "dirty": "clean",
        "pr": "",
        "draft": "",
        "status": "skipped",
        "action": "skip-dirty",
        "target": "",
        "message": "worktree has local changes",
    }
    defaults.update(overrides)
    return apply_sync.PlanRecord(**defaults)


def _record_to_json(rec: Any) -> str:
    """Serialize a PlanRecord to a JSON string via dataclasses.asdict."""
    return json.dumps(dataclasses.asdict(rec))


def test_read_plan_from_stdin_does_not_call_plan_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--from-plan-stdin must not invoke plan_one at all."""
    plan_one_calls: list[Any] = []

    def spy_plan_one(*args: Any, **kwargs: Any) -> Any:
        plan_one_calls.append(args)
        raise AssertionError("plan_one must not be called in --from-plan-stdin mode")

    monkeypatch.setattr(apply_sync, "plan_one", spy_plan_one)

    rec = _make_plan_record()
    stdin_text = _record_to_json(rec) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))

    result = apply_sync.read_plan_from_stdin()

    assert plan_one_calls == [], "plan_one was called unexpectedly"
    assert len(result) == 1


def test_read_plan_from_stdin_deserializes_single_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A single JSONL line must deserialize to the matching PlanRecord."""
    rec = apply_sync.PlanRecord(
        path="/some/repo",
        branch="fix/bug",
        dirty="clean",
        pr="42",
        draft="no",
        status="planned",
        action="rebase-default",
        target="origin/main",
        message="draft PR or private branch without remote tracking branch",
    )
    stdin_text = _record_to_json(rec) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))

    result = apply_sync.read_plan_from_stdin()

    assert result == [rec]


def test_read_plan_from_stdin_preserves_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Multiple JSONL lines must deserialize in input order."""
    recs = [
        _make_plan_record(path=f"/repo-{i}", branch=f"feature/{i}") for i in range(3)
    ]
    lines = "\n".join(_record_to_json(r) for r in recs) + "\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(lines))

    result = apply_sync.read_plan_from_stdin()

    assert result == recs


def test_read_plan_from_stdin_skips_empty_lines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Blank lines (whitespace-only) must be silently skipped."""
    rec = _make_plan_record()
    payload = _record_to_json(rec)
    stdin_text = f"\n  \n{payload}\n\n"
    monkeypatch.setattr("sys.stdin", io.StringIO(stdin_text))

    result = apply_sync.read_plan_from_stdin()

    assert len(result) == 1
    assert result[0] == rec


def test_read_plan_from_stdin_invalid_json_exits_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An invalid JSON line must print to stderr and raise SystemExit(2)."""
    monkeypatch.setattr("sys.stdin", io.StringIO("not-valid-json\n"))

    with pytest.raises(SystemExit) as exc_info:
        apply_sync.read_plan_from_stdin()

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "line 1" in captured.err
    assert "not-valid-json" in captured.err


def test_main_without_from_plan_stdin_calls_plan_one(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Without --from-plan-stdin, main() must invoke plan_one (legacy path intact)."""
    plan_one_calls: list[Any] = []
    skipped_rec = _make_plan_record(status="skipped", action="skip-dirty")

    def fake_plan_one(worktree: Any, default: str) -> Any:
        plan_one_calls.append(worktree)
        return skipped_rec

    monkeypatch.setattr(apply_sync, "plan_one", fake_plan_one)
    monkeypatch.setattr(
        apply_sync,
        "list_worktrees",
        lambda root: [object()],
    )
    monkeypatch.setattr(
        apply_sync,
        "default_branch",
        lambda root: "main",
    )
    monkeypatch.setattr(apply_sync, "apply_plan", lambda r: r)
    monkeypatch.setattr(
        "sys.argv",
        ["apply_linked_worktree_sync.py", "--format", "jsonl"],
    )

    exit_code = apply_sync.main()

    assert len(plan_one_calls) == 1, "plan_one must be called exactly once per worktree"
    assert exit_code == 0


# ---------------------------------------------------------------------------
# Tests for failure / state-transition scenarios (tracker #60 item 7)
# ---------------------------------------------------------------------------


def test_apply_plan_fetch_failure_does_not_call_merge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """fetch failure must short-circuit: merge must not be called."""
    git_calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        if args[:1] == ["fetch"]:
            return completed(args, stderr="network error", returncode=1)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("pull-default"))

    assert result.status == "failed"
    assert result.message == "network error"
    assert not any(a[:1] == ["merge"] for a in git_calls), (
        "merge must not be called after fetch failure"
    )


def test_apply_plan_non_origin_target_skips_fetch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """target that does not start with 'origin/' must skip fetch entirely."""
    git_calls: list[list[str]] = []
    heads = iter(["before", "after"])

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout=f"{next(heads)}\n")
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("pull-default", target="refs/heads/main"))

    assert not any(a[:1] == ["fetch"] for a in git_calls), (
        "fetch must not be called for non-origin target"
    )
    assert result.status in ("updated", "noop")


def test_apply_plan_pull_default_merge_failure_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """merge --ff-only non-zero exit must set status='failed' with summarize message."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["merge"]:
            return completed(args, stderr="Not possible to fast-forward.", returncode=1)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("pull-default"))

    assert result.status == "failed"
    assert result.message == "Not possible to fast-forward."


def test_apply_plan_rebase_branch_failure_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rebase non-zero exit (rebase-branch) must set status='failed' with abort suffix."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["rebase", "--abort"]:
            return completed(args)
        if args[:1] == ["rebase"]:
            return completed(
                args,
                stderr="CONFLICT (content): Merge conflict",
                returncode=1,
            )
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("rebase-branch", "origin/feature/x"))

    assert result.status == "failed"
    assert result.message == "CONFLICT (content): Merge conflict; rebase aborted"


def test_apply_plan_rebase_default_failure_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """rebase non-zero exit (rebase-default) must set status='failed' with abort suffix."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["rebase", "--abort"]:
            return completed(args)
        if args[:1] == ["rebase"]:
            return completed(args, stderr="rebase: nothing to rebase", returncode=1)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("rebase-default"))

    assert result.status == "failed"
    assert result.message == "rebase: nothing to rebase; rebase aborted"


def test_apply_plan_retire_contained_switch_failure_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """git switch -C non-zero exit (retire-contained) must set status='failed'."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["switch"]:
            return completed(args, stderr="fatal: not a valid branch", returncode=1)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("retire-contained"))

    assert result.status == "failed"
    assert result.message == "fatal: not a valid branch"


def test_apply_plan_retire_merged_pr_switch_failure_returns_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """git switch -C non-zero exit (retire-merged-pr) must set status='failed'."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args[:1] == ["switch"]:
            return completed(args, stderr="fatal: cannot switch", returncode=128)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("retire-merged-pr"))

    assert result.status == "failed"
    assert result.message == "fatal: cannot switch"


def test_apply_plan_pull_default_noop_when_head_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """pull-default where HEAD does not advance must yield status='noop'."""

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        if args == ["rev-parse", "HEAD"]:
            return completed(args, stdout="deadbeef\n")
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    result = apply_sync.apply_plan(record("pull-default"))

    assert result.status == "noop"
    assert result.message == "already up to date"


def test_apply_plan_unsupported_action_returns_failed_without_git_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unknown action must set status='failed' with 'unsupported action:' message.

    fetch IS called (it runs before the action dispatch), but no git merge/rebase/switch
    should be called, since we return early from the else branch.
    """
    git_calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        return completed(args, stdout="abc123\n")

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    unknown_rec = apply_sync.PlanRecord(
        path="/repo",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="planned",
        action="unknown",
        target="origin/main",
        message="planned",
    )
    result = apply_sync.apply_plan(unknown_rec)

    assert result.status == "failed"
    assert result.message == "unsupported action: unknown"
    assert not any(a[:1] in (["merge"], ["rebase"], ["switch"]) for a in git_calls), (
        "merge/rebase/switch must not be called for unsupported action"
    )


def test_apply_plan_non_planned_status_passthrough_dirty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Records with status other than 'planned' must be returned as-is.

    No git calls should be made.
    """
    git_calls: list[list[str]] = []

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        git_calls.append(args)
        return completed(args)

    monkeypatch.setattr(apply_sync, "run_git", fake_run_git)

    for non_planned_status in (
        "dirty",
        "failed",
        "noop",
        "updated",
        "settled",
        "skipped",
    ):
        dirty_rec = apply_sync.PlanRecord(
            path="/repo",
            branch="feature/test",
            dirty="dirty",
            pr="",
            draft="",
            status=non_planned_status,
            action="pull-default",
            target="origin/main",
            message="some prior message",
        )
        result = apply_sync.apply_plan(dirty_rec)
        assert result is dirty_rec, (
            f"status={non_planned_status!r} must be passed through"
        )

    assert git_calls == [], "no git commands must be issued for non-planned records"


def test_main_exit_code_one_when_any_record_failed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() must return exit code 1 when at least one record has status='failed'."""
    applied_ok = _make_plan_record(
        status="updated",
        action="pull-default",
        target="origin/main",
    )
    applied_fail = _make_plan_record(
        status="failed",
        action="pull-default",
        target="origin/main",
        path="/repo2",
    )
    # apply_plan results: first=ok, second=failed - iterator drives the sequence
    apply_results = iter([applied_ok, applied_fail])

    monkeypatch.setattr(apply_sync, "plan_one", lambda wt, d: applied_ok)
    monkeypatch.setattr(apply_sync, "list_worktrees", lambda root: [object(), object()])
    monkeypatch.setattr(apply_sync, "default_branch", lambda root: "main")
    monkeypatch.setattr(apply_sync, "apply_plan", lambda r: next(apply_results))
    monkeypatch.setattr(
        "sys.argv",
        ["apply_linked_worktree_sync.py", "--format", "jsonl"],
    )

    exit_code = apply_sync.main()

    assert exit_code == 1


def test_main_exit_code_zero_when_no_record_failed(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() must return exit code 0 when no record has status='failed'."""
    applied_ok = _make_plan_record(
        status="updated",
        action="pull-default",
        target="origin/main",
    )
    applied_noop = _make_plan_record(
        status="noop",
        action="pull-default",
        target="origin/main",
    )
    applied_settled = _make_plan_record(
        status="settled",
        action="retire-contained",
        target="origin/main",
    )

    results = iter([applied_ok, applied_noop, applied_settled])

    monkeypatch.setattr(apply_sync, "plan_one", lambda wt, d: applied_ok)
    monkeypatch.setattr(
        apply_sync,
        "list_worktrees",
        lambda root: [object(), object(), object()],
    )
    monkeypatch.setattr(apply_sync, "default_branch", lambda root: "main")
    monkeypatch.setattr(apply_sync, "apply_plan", lambda r: next(results))
    monkeypatch.setattr(
        "sys.argv",
        ["apply_linked_worktree_sync.py", "--format", "jsonl"],
    )

    exit_code = apply_sync.main()

    assert exit_code == 0
