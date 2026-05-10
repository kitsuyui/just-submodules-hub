from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/apply_linked_worktree_sync.py"

spec = importlib.util.spec_from_file_location("apply_linked_worktree_sync", SCRIPT_PATH)
assert spec is not None
apply_sync = importlib.util.module_from_spec(spec)
sys.modules["apply_linked_worktree_sync"] = apply_sync
assert spec.loader is not None
spec.loader.exec_module(apply_sync)


def record(action: str, target: str = "origin/main") -> object:
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
