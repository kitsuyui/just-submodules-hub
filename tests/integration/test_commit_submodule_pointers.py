from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, advance_remote, create_remote, run

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_commit_submodule_pointers_creates_parent_commit(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "pointers",
        {"README.md": "before\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/example-owner/pointers")
    advance_remote(remote, "README.md", "after\n", "Update remote")

    sync_proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "sync-repo-default-branch",
            "repo/github.com/example-owner/pointers",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert sync_proc.returncode == 0, sync_proc.stderr

    commit_proc = subprocess.run(
        [str(ACTION_SCRIPT), "commit-submodule-pointers", "Update submodule pointers"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert commit_proc.returncode == 0, commit_proc.stderr
    assert (
        run(["git", "log", "-1", "--pretty=%s"], cwd=hub_repo)
        == "Update submodule pointers"
    )


def test_commit_submodule_pointers_works_when_submodules_are_ignored_all(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "ignored-pointers",
        {"README.md": "before\n"},
    )
    submodule_path = "repo/github.com/example-owner/ignored-pointers"
    section = "submodule.repo/github.com/example-owner/ignored-pointers"
    add_submodule(hub_repo, remote, submodule_path)
    advance_remote(remote, "README.md", "after\n", "Update remote")

    sync_proc = subprocess.run(
        [str(ACTION_SCRIPT), "sync-repo-default-branch", submodule_path],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert sync_proc.returncode == 0, sync_proc.stderr

    run(["git", "config", "--local", f"{section}.ignore", "all"], cwd=hub_repo)

    commit_proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "commit-submodule-pointers",
            "Update ignored submodule pointers",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert commit_proc.returncode == 0, commit_proc.stderr
    assert (
        run(["git", "log", "-1", "--pretty=%s"], cwd=hub_repo)
        == "Update ignored submodule pointers"
    )


def test_commit_submodule_pointers_selected_repo_leaves_other_pointers_unstaged(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    first_remote = create_remote(
        tmp_path,
        "example-owner",
        "first",
        {"README.md": "before\n"},
    )
    second_remote = create_remote(
        tmp_path,
        "example-owner",
        "second",
        {"README.md": "before\n"},
    )
    first_path = "repo/github.com/example-owner/first"
    second_path = "repo/github.com/example-owner/second"
    add_submodule(hub_repo, first_remote, first_path)
    add_submodule(hub_repo, second_remote, second_path)
    advance_remote(first_remote, "README.md", "after\n", "Update first remote")
    advance_remote(second_remote, "README.md", "after\n", "Update second remote")

    for submodule_path in (first_path, second_path):
        sync_proc = subprocess.run(
            [str(ACTION_SCRIPT), "sync-repo-default-branch", submodule_path],
            cwd=str(hub_repo),
            text=True,
            capture_output=True,
            check=False,
        )
        assert sync_proc.returncode == 0, sync_proc.stderr

    before_head = run(["git", "rev-parse", "HEAD"], cwd=hub_repo)
    commit_proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "commit-submodule-pointers",
            "Update first pointer",
            "example-owner/first",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert commit_proc.returncode == 0, commit_proc.stderr
    assert (
        run(["git", "log", "-1", "--pretty=%s"], cwd=hub_repo) == "Update first pointer"
    )

    committed_paths = run(
        ["git", "diff", "--name-only", before_head, "HEAD"],
        cwd=hub_repo,
    ).splitlines()
    assert committed_paths == [first_path]

    staged_paths = run(["git", "diff", "--cached", "--name-only"], cwd=hub_repo)
    assert staged_paths == ""
    unstaged_paths = run(
        ["git", "diff", "--name-only", "--ignore-submodules=none"],
        cwd=hub_repo,
    ).splitlines()
    assert unstaged_paths == [second_path]


def test_commit_submodule_pointers_rejects_unregistered_repo(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "registered",
        {"README.md": "before\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/example-owner/registered")

    commit_proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "commit-submodule-pointers",
            "Update missing pointer",
            "example-owner/missing",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert commit_proc.returncode == 1
    assert "not a registered submodule" in commit_proc.stderr
