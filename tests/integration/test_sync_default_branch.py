from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, advance_remote, create_remote, git_head

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_sync_default_branch_updates_submodule_to_latest(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "sync-me",
        {"README.md": "hello\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/example-owner/sync-me")
    latest_head = advance_remote(remote, "README.md", "hello again\n", "Update README")

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "sync-repo-default-branch",
            "repo/github.com/example-owner/sync-me",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert git_head(hub_repo / "repo/github.com/example-owner/sync-me") == latest_head


def test_sync_default_branch_resolves_unique_short_name(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "sync-me",
        {"README.md": "hello\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/example-owner/sync-me")
    latest_head = advance_remote(remote, "README.md", "hello again\n", "Update README")

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "sync-repo-default-branch", "sync-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert git_head(hub_repo / "repo/github.com/example-owner/sync-me") == latest_head
