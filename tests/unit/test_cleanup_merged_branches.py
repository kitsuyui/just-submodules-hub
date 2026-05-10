from __future__ import annotations

from pathlib import Path

import pytest

import just_submodules_hub.branch_cleanup as cleanup


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


def test_cleanup_repo_force_deletes_squash_or_rebase_merged_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Squash/rebase-merged branches must be deleted via -D, not reported failed.

    ``git branch -d`` refuses to delete a branch whose commits are not
    reachable from HEAD as the same SHAs, which is the normal squash-merge
    or rebase-merge case. When the branch is already in merged_pr_heads,
    the work is preserved on the remote via the merged PR, so falling back
    to ``-D`` is safe and is what users want. Without this fallback, the
    most common cleanup case appears as ``failed`` and the CLI exits 1.
    """
    calls: list[list[str]] = []
    monkeypatch.setattr(
        cleanup,
        "inspect_state",
        lambda repo, remote, limit: branch_state(),
    )

    def fake_run_git(repo: Path, args: list[str]) -> object:
        calls.append(args)
        # Local ``-d`` for feature/merged simulates the squash-merge refusal.
        if args == ["branch", "-d", "feature/merged"]:
            return type(
                "Proc",
                (),
                {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": (
                        "error: The branch 'feature/merged' is not fully merged."
                    ),
                },
            )()
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

    # ``-d`` was tried first and refused, so ``-D`` was used as fallback.
    assert ["branch", "-d", "feature/merged"] in calls
    assert ["branch", "-D", "feature/merged"] in calls

    by_target_branch = {(row.target, row.branch): row for row in rows}
    local_merged = by_target_branch[("local", "feature/merged")]
    assert local_merged.status == "deleted"
    assert "force-deleted" in local_merged.reason
    assert "squash" in local_merged.reason


def test_cleanup_repo_reports_failed_when_force_delete_also_fails(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """If both -d and -D fail, report failed with the -D error message."""
    monkeypatch.setattr(
        cleanup,
        "inspect_state",
        lambda repo, remote, limit: branch_state(),
    )

    def fake_run_git(repo: Path, args: list[str]) -> object:
        if args == ["branch", "-d", "feature/merged"]:
            return type(
                "Proc",
                (),
                {"returncode": 1, "stdout": "", "stderr": "not fully merged"},
            )()
        if args == ["branch", "-D", "feature/merged"]:
            return type(
                "Proc",
                (),
                {"returncode": 1, "stdout": "", "stderr": "permission denied"},
            )()
        return type("Proc", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(cleanup, "run_git", fake_run_git)

    rows = cleanup.cleanup_repo(
        tmp_path,
        ".",
        include_local=True,
        include_remote=False,
        include_non_owner_remote=False,
        remote="origin",
        apply=True,
        limit=200,
    )

    by_target_branch = {(row.target, row.branch): row for row in rows}
    local_merged = by_target_branch[("local", "feature/merged")]
    assert local_merged.status == "failed"
    assert "permission denied" in local_merged.reason


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


def test_linked_worktree_branches_parses_porcelain_output(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """``linked_worktree_branches`` extracts branch names from worktree list output."""

    def fake_run_git(repo: Path, args: list[str]) -> object:
        assert args == ["worktree", "list", "--porcelain"]
        return type(
            "Proc",
            (),
            {
                "returncode": 0,
                "stdout": (
                    "worktree /path/to/main\n"
                    "HEAD abc\n"
                    "branch refs/heads/main\n"
                    "\n"
                    "worktree /path/to/feature\n"
                    "HEAD def\n"
                    "branch refs/heads/feature/x\n"
                    "\n"
                    "worktree /path/to/detached\n"
                    "HEAD 999\n"
                    "detached\n"
                ),
                "stderr": "",
            },
        )()

    monkeypatch.setattr(cleanup, "run_git", fake_run_git)

    assert cleanup.linked_worktree_branches(tmp_path) == frozenset(
        {"main", "feature/x"},
    )


def test_linked_worktree_branches_returns_empty_on_failure(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Failures in ``git worktree list`` must not crash callers."""

    def fake_run_git(repo: Path, args: list[str]) -> object:
        return type(
            "Proc",
            (),
            {"returncode": 128, "stdout": "", "stderr": "fatal: not a worktree"},
        )()

    monkeypatch.setattr(cleanup, "run_git", fake_run_git)

    assert cleanup.linked_worktree_branches(tmp_path) == frozenset()


def test_protected_reason_skips_branches_in_other_worktrees() -> None:
    """A branch checked out in a linked worktree must be skipped, not deleted."""
    state = cleanup.BranchState(
        default_branch="main",
        current_branch="main",
        local_branches=("main", "feature/in-worktree", "feature/free"),
        remote_branches=(),
        merged_pr_heads=frozenset({"feature/in-worktree", "feature/free"}),
        owned_merged_pr_heads=frozenset({"feature/in-worktree", "feature/free"}),
        open_pr_heads=frozenset(),
        worktree_branches=frozenset({"main", "feature/in-worktree"}),
    )

    # Current branch protection still wins for the main worktree's branch.
    assert cleanup.protected_reason("main", state) == "default branch"
    # A branch occupied by a linked worktree is reported with a clear reason.
    assert (
        cleanup.protected_reason("feature/in-worktree", state)
        == "checked out in another worktree"
    )
    # Unprotected branch is unaffected.
    assert cleanup.protected_reason("feature/free", state) == ""


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
