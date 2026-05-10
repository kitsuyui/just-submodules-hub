from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/cleanup_merged_branches.py"

spec = importlib.util.spec_from_file_location("cleanup_merged_branches", SCRIPT_PATH)
assert spec is not None
cleanup = importlib.util.module_from_spec(spec)
sys.modules["cleanup_merged_branches"] = cleanup
assert spec.loader is not None
spec.loader.exec_module(cleanup)


def branch_state() -> object:
    return cleanup.BranchState(
        default_branch="main",
        current_branch="feature/current",
        local_branches=(
            "main",
            "feature/current",
            "feature/merged",
            "feature/open",
            "feature/other",
        ),
        remote_branches=(
            "main",
            "feature/merged",
            "feature/other-merged",
            "feature/open",
            "feature/other",
        ),
        merged_pr_heads=frozenset({"feature/merged", "feature/other-merged"}),
        owned_merged_pr_heads=frozenset({"feature/merged"}),
        open_pr_heads=frozenset({"feature/open"}),
    )


def test_cleanup_repo_reports_dry_run_candidates(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        cleanup,
        "inspect_state",
        lambda repo, remote, limit: branch_state(),
    )

    rows = cleanup.cleanup_repo(
        tmp_path,
        ".",
        include_local=True,
        include_remote=True,
        include_non_owner_remote=False,
        remote="origin",
        apply=False,
        limit=200,
    )

    by_target_branch = {(row.target, row.branch): row for row in rows}
    assert by_target_branch[("local", "feature/merged")].status == "would-delete"
    assert by_target_branch[("remote", "feature/merged")].status == "would-delete"
    assert (
        by_target_branch[("remote", "feature/other-merged")].reason
        == "merged pull request not owned by authenticated user"
    )
    assert by_target_branch[("local", "main")].reason == "default branch"
    assert by_target_branch[("local", "feature/current")].reason == "current branch"
    assert by_target_branch[("remote", "feature/open")].reason == "open pull request"
    assert (
        by_target_branch[("remote", "feature/other")].reason == "no merged pull request"
    )


def test_cleanup_repo_deletes_only_merged_candidates_when_apply(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(
        cleanup,
        "inspect_state",
        lambda repo, remote, limit: branch_state(),
    )

    def fake_run_git(repo: Path, args: list[str]) -> object:
        calls.append(args)
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(cleanup, "run_git", fake_run_git)

    rows = cleanup.cleanup_repo(
        tmp_path,
        ".",
        include_local=True,
        include_remote=True,
        include_non_owner_remote=True,
        remote="origin",
        apply=True,
        limit=200,
    )

    assert ["branch", "-d", "feature/merged"] in calls
    assert ["push", "origin", "--delete", "feature/merged"] in calls
    assert ["push", "origin", "--delete", "feature/other-merged"] in calls
    assert all(
        row.status != "deleted"
        or row.branch in {"feature/merged", "feature/other-merged"}
        for row in rows
    )


def test_target_paths_can_include_root_and_submodules(tmp_path: Path) -> None:
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "repo/github.com/example/a"]
    path = repo/github.com/example/a
""".strip(),
        encoding="utf-8",
    )

    assert cleanup.target_paths(tmp_path, "one") == ["."]
    assert cleanup.target_paths(tmp_path, "all") == ["repo/github.com/example/a"]
    assert cleanup.target_paths(tmp_path, "root-and-all") == [
        ".",
        "repo/github.com/example/a",
    ]


def test_remote_branches_reads_actual_remote_heads(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fake_run_git(repo: Path, args: list[str]) -> object:
        assert args == ["ls-remote", "--heads", "origin"]
        return type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": "abc\trefs/heads/main\n123\trefs/heads/feature/merged\n",
                "stderr": "",
            },
        )()

    monkeypatch.setattr(cleanup, "run_git", fake_run_git)

    assert cleanup.remote_branches(tmp_path, "origin") == ("main", "feature/merged")


def test_cleanup_repo_skips_repositories_without_pr_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_inspect(repo: Path, remote: str, limit: int) -> object:
        raise RuntimeError(
            "GraphQL: Could not resolve to a Repository"
            " with the name 'owner/repo.wiki'.",
        )

    monkeypatch.setattr(cleanup, "inspect_state", fail_inspect)

    rows = cleanup.cleanup_repo(
        tmp_path,
        "repo/github.com/owner/repo.wiki",
        include_local=True,
        include_remote=True,
        include_non_owner_remote=False,
        remote="origin",
        apply=False,
        limit=200,
    )

    assert rows == [
        cleanup.BranchResult(
            "repo/github.com/owner/repo.wiki",
            "repo",
            "",
            "skipped",
            "GraphQL: Could not resolve to a Repository"
            " with the name 'owner/repo.wiki'.",
        ),
    ]


def test_cleanup_repo_skips_non_owner_remote_branches_by_default(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        cleanup,
        "inspect_state",
        lambda repo, remote, limit: branch_state(),
    )

    rows = cleanup.cleanup_repo(
        tmp_path,
        "repo/github.com/example/project",
        include_local=False,
        include_remote=True,
        include_non_owner_remote=False,
        remote="origin",
        apply=False,
        limit=200,
    )

    by_branch = {row.branch: row for row in rows}
    assert by_branch["feature/merged"].status == "would-delete"
    assert (
        by_branch["feature/other-merged"].reason
        == "merged pull request not owned by authenticated user"
    )
