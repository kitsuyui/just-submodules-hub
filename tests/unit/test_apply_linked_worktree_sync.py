from __future__ import annotations

import dataclasses
import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/apply_linked_worktree_sync.py"

spec = importlib.util.spec_from_file_location("apply_linked_worktree_sync", SCRIPT_PATH)
assert spec is not None
apply_sync = importlib.util.module_from_spec(spec)
sys.modules["apply_linked_worktree_sync"] = apply_sync
assert spec.loader is not None
spec.loader.exec_module(apply_sync)


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
    args: list[str], stdout: str = "", stderr: str = "", returncode: int = 0
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def test_apply_plan_leaves_skipped_records_unchanged() -> None:
    skipped = apply_sync.PlanRecord(
        "/repo", "feature/test", "dirty", "", "", "skipped", "skip-dirty", "", "dirty"
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
    defaults: dict[str, str] = dict(
        path="/repo",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="skipped",
        action="skip-dirty",
        target="",
        message="worktree has local changes",
    )
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
        "sys.argv", ["apply_linked_worktree_sync.py", "--format", "jsonl"]
    )

    exit_code = apply_sync.main()

    assert len(plan_one_calls) == 1, "plan_one must be called exactly once per worktree"
    assert exit_code == 0
