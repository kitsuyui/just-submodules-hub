from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/linked_worktree_safety.py"

spec = importlib.util.spec_from_file_location("linked_worktree_safety", SCRIPT_PATH)
assert spec is not None
safety = importlib.util.module_from_spec(spec)
sys.modules["linked_worktree_safety"] = safety
assert spec.loader is not None
spec.loader.exec_module(safety)


def test_install_hooks_keeps_existing_hook_and_writes_sample(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo"
    hooks = repo / ".git" / "hooks"
    hooks.mkdir(parents=True)
    hook = hooks / "pre-push"
    hook.write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr(safety, "git_common_dir", lambda root: repo / ".git")

    record = safety.install_hooks(repo)

    assert record.status == "skipped"
    assert hook.read_text(encoding="utf-8") == "existing\n"
    assert (hooks / "pre-push.linked-worktrees.sample").exists()


def test_reset_record_plans_backup_without_apply(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo-feature"
    repo.mkdir()
    monkeypatch.setattr(safety, "current_branch", lambda repo: "feature/test")
    monkeypatch.setattr(safety, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(safety, "default_branch", lambda repo: "main")
    monkeypatch.setattr(safety, "timestamp", lambda: "20260428000000")

    assert safety.reset_record(
        repo, target="", backup_prefix="stash", apply=False
    ) == safety.ResetRecord(
        path=str(repo),
        branch="feature/test",
        status="planned",
        action="reset",
        backup="stash/repo-feature/20260428000000",
        target="origin/main",
        message="dry-run",
    )


def test_reset_record_apply_creates_backup_before_reset(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo = tmp_path / "repo-feature"
    repo.mkdir()
    calls: list[list[str]] = []
    monkeypatch.setattr(safety, "current_branch", lambda repo: "feature/test")
    monkeypatch.setattr(safety, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(safety, "current_head", lambda repo: "abc123")
    monkeypatch.setattr(safety, "timestamp", lambda: "20260428000000")

    def fake_run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
        calls.append(args)
        return subprocess.CompletedProcess(["git", *args], 0, "", "")

    monkeypatch.setattr(safety, "run_git", fake_run_git)

    record = safety.reset_record(
        repo, target="origin/main", backup_prefix="stash", apply=True
    )

    assert record.status == "settled"
    assert calls == [
        ["fetch", "origin", "main"],
        ["branch", "stash/repo-feature/20260428000000", "abc123"],
        ["switch", "-C", "feature/test", "origin/main"],
    ]


def test_cleanup_records_plans_only_retire_candidates(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    feature = tmp_path / "repo-feature"
    feature.mkdir()
    worktrees = [
        safety.WorktreeRecord(str(root), "1", "main", "no", "no", "no", ""),
        safety.WorktreeRecord(str(feature), "2", "feature/test", "no", "no", "no", ""),
    ]
    monkeypatch.setattr(safety, "default_branch", lambda root: "main")
    monkeypatch.setattr(safety, "list_worktrees", lambda root: worktrees)
    monkeypatch.setattr(
        safety,
        "plan_one",
        lambda worktree, default: safety.PlanRecord(
            worktree.path,
            worktree.branch,
            "clean",
            "",
            "",
            "planned",
            "retire-contained",
            "origin/main",
            "contained",
        ),
    )

    assert safety.cleanup_records(
        root, path_glob="repo-*", apply=False, drop_branch=False, include_skipped=False
    ) == [
        safety.CleanupRecord(
            str(feature), "feature/test", "planned", "remove", "dry-run"
        )
    ]
