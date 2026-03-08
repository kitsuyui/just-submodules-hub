from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, advance_remote, create_remote, init_hub, run


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT = PROJECT_ROOT / "scripts/repo/sync-default-branch.sh"


def write_consumer_justfile(hub_repo: Path) -> None:
    justfile = hub_repo / "justfile"
    justfile.write_text(f'import "{PROJECT_ROOT / "just/index.just"}"\n', encoding="utf-8")


def test_imported_repo_submodule_list_managed_uses_consumer_invocation_directory(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    remote = create_remote(tmp_path, "acme", "managed", {"README.md": "hello\n"})
    add_submodule(hub_repo, remote, "repo/github.com/acme/managed")

    proc = subprocess.run(
        ["just", "repo", "submodule", "list-managed"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["acme/managed"]


def test_imported_repo_submodule_commit_pointers_uses_consumer_invocation_directory(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    remote = create_remote(tmp_path, "acme", "pointers", {"README.md": "before\n"})
    add_submodule(hub_repo, remote, "repo/github.com/acme/pointers")
    advance_remote(remote, "README.md", "after\n", "Update remote")

    sync_proc = subprocess.run(
        [str(SYNC_SCRIPT), "one", "repo/github.com/acme/pointers"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert sync_proc.returncode == 0, sync_proc.stderr

    commit_proc = subprocess.run(
        ["just", "repo", "submodule", "commit-pointers", "Update submodule pointers"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert commit_proc.returncode == 0, commit_proc.stderr
    assert run(["git", "log", "-1", "--pretty=%s"], cwd=hub_repo) == "Update submodule pointers"
