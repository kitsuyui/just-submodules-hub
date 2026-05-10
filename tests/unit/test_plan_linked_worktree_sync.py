from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

import just_submodules_hub.linked_worktree_planning as planner


def completed(
    args: list[str],
    stdout: str = "",
    stderr: str = "",
    returncode: int = 0,
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args, returncode, stdout, stderr)


def worktree(
    branch: str = "feature/test",
    *,
    path: str = "/repo-feature",
    detached: str = "no",
) -> planner.WorktreeRecord:
    return planner.WorktreeRecord(
        path=path,
        head="1111111111111111111111111111111111111111",
        branch=branch,
        detached=detached,
        locked="no",
        prunable="no",
        message="",
    )


def test_plan_one_skips_dirty_worktree(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(planner, "dirty_state", lambda repo: "dirty")

    assert planner.plan_one(worktree(), "main") == planner.PlanRecord(
        path="/repo-feature",
        branch="feature/test",
        dirty="dirty",
        pr="",
        draft="",
        status="skipped",
        action="skip-dirty",
        target="",
        message="worktree has local changes",
    )


def test_plan_one_retires_branch_without_unique_commits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(
        planner,
        "branch_has_unique_commits",
        lambda repo, branch, default: False,
    )

    assert planner.plan_one(worktree(), "main") == planner.PlanRecord(
        path="/repo-feature",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="planned",
        action="retire-contained",
        target="origin/main",
        message="branch has no commits outside default branch",
    )


def test_plan_one_skips_open_non_draft_pull_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(
        planner,
        "branch_has_unique_commits",
        lambda repo, branch, default: True,
    )
    monkeypatch.setattr(
        planner,
        "gh_pr_view",
        lambda repo: planner.PullRequestState("12", "open", "no", ""),
    )

    assert planner.plan_one(worktree(), "main") == planner.PlanRecord(
        path="/repo-feature",
        branch="feature/test",
        dirty="clean",
        pr="12",
        draft="no",
        status="skipped",
        action="skip-open-pr",
        target="",
        message="open non-draft pull request",
    )


def test_plan_one_rebases_draft_pr_to_remote_branch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(
        planner,
        "branch_has_unique_commits",
        lambda repo, branch, default: True,
    )
    monkeypatch.setattr(
        planner,
        "gh_pr_view",
        lambda repo: planner.PullRequestState("12", "open", "yes", ""),
    )
    monkeypatch.setattr(planner, "remote_branch_exists", lambda repo, branch: True)

    assert planner.plan_one(worktree(), "main") == planner.PlanRecord(
        path="/repo-feature",
        branch="feature/test",
        dirty="clean",
        pr="12",
        draft="yes",
        status="planned",
        action="rebase-branch",
        target="origin/feature/test",
        message="draft PR or private branch with remote tracking branch",
    )


def test_plan_one_skips_when_pr_metadata_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(planner, "dirty_state", lambda repo: "clean")
    monkeypatch.setattr(
        planner,
        "branch_has_unique_commits",
        lambda repo, branch, default: True,
    )
    monkeypatch.setattr(
        planner,
        "gh_pr_view",
        lambda repo: planner.PullRequestState("", "unknown", "", "gh not found"),
    )

    assert planner.plan_one(worktree(), "main") == planner.PlanRecord(
        path="/repo-feature",
        branch="feature/test",
        dirty="clean",
        pr="",
        draft="",
        status="skipped",
        action="skip-pr-unknown",
        target="",
        message="gh not found",
    )


def test_gh_pr_view_treats_missing_pr_as_none(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: "/usr/bin/gh")

    def fake_run(*args: object, **kwargs: object) -> subprocess.CompletedProcess[str]:
        return completed([], stderr="no pull requests found for branch", returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert planner.gh_pr_view(tmp_path) == planner.PullRequestState(
        "",
        "none",
        "",
        "no pull request metadata",
    )
