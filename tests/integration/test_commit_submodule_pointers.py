from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, advance_remote, create_remote, run


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = PROJECT_ROOT / "scripts/repo/sync-default-branch.sh"
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_commit_submodule_pointers_creates_parent_commit(tmp_path: Path, hub_repo: Path) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "pointers",
        {"README.md": "before\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/example-owner/pointers")
    advance_remote(remote, "README.md", "after\n", "Update remote")

    sync_proc = subprocess.run(
        [str(SYNC_SCRIPT), "one", "repo/github.com/example-owner/pointers"],
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
    assert run(["git", "log", "-1", "--pretty=%s"], cwd=hub_repo) == "Update submodule pointers"
