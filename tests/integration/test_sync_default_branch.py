from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, advance_remote, create_remote, git_head


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/repo/sync-default-branch.sh"


def test_sync_default_branch_updates_submodule_to_latest(tmp_path: Path, hub_repo: Path) -> None:
    remote = create_remote(
        tmp_path,
        "acme",
        "sync-me",
        {"README.md": "hello\n"},
    )
    add_submodule(hub_repo, remote, "repo/github.com/acme/sync-me")
    latest_head = advance_remote(remote, "README.md", "hello again\n", "Update README")

    proc = subprocess.run(
        [str(SCRIPT), "one", "repo/github.com/acme/sync-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert git_head(hub_repo / "repo/github.com/acme/sync-me") == latest_head
