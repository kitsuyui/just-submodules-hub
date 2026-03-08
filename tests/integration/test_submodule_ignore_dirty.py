from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, run


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_submodule_ignore_dirty_toggle_updates_local_config(tmp_path: Path, hub_repo: Path) -> None:
    remote = create_remote(
        tmp_path,
        "acme",
        "ignore-me",
        {"README.md": "hello\n"},
    )
    submodule_path = "repo/github.com/acme/ignore-me"
    section = "submodule.repo/github.com/acme/ignore-me"
    add_submodule(hub_repo, remote, submodule_path)

    on_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-on"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert on_proc.returncode == 0, on_proc.stderr
    assert run(["git", "config", "--local", "--get", f"{section}.ignore"], cwd=hub_repo) == "dirty"

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-status"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert f"{submodule_path}\tdirty" in status_proc.stdout.splitlines()

    off_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-off"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert off_proc.returncode == 0, off_proc.stderr
    get_proc = subprocess.run(
        ["git", "config", "--local", "--get", f"{section}.ignore"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert get_proc.returncode != 0

    status_after_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-status"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_after_proc.returncode == 0, status_after_proc.stderr
    assert f"{submodule_path}\toff" in status_after_proc.stdout.splitlines()
