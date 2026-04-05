from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, run


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_submodule_ignore_dirty_toggle_updates_local_config(tmp_path: Path, hub_repo: Path) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "ignore-me",
        {"README.md": "hello\n"},
    )
    submodule_path = "repo/github.com/example-owner/ignore-me"
    section = "submodule.repo/github.com/example-owner/ignore-me"
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


def test_submodule_ignore_dirty_toggle_supports_targeted_repo(tmp_path: Path, hub_repo: Path) -> None:
    remote_a = create_remote(
        tmp_path,
        "example-owner",
        "ignore-me",
        {"README.md": "hello\n"},
    )
    remote_b = create_remote(
        tmp_path,
        "example-owner",
        "keep-visible",
        {"README.md": "world\n"},
    )
    path_a = "repo/github.com/example-owner/ignore-me"
    path_b = "repo/github.com/example-owner/keep-visible"
    section_a = "submodule.repo/github.com/example-owner/ignore-me"
    section_b = "submodule.repo/github.com/example-owner/keep-visible"

    add_submodule(hub_repo, remote_a, path_a)
    add_submodule(hub_repo, remote_b, path_b)

    on_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-on", "example-owner/ignore-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert on_proc.returncode == 0, on_proc.stderr
    assert run(["git", "config", "--local", "--get", f"{section_a}.ignore"], cwd=hub_repo) == "dirty"

    get_b_proc = subprocess.run(
        ["git", "config", "--local", "--get", f"{section_b}.ignore"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert get_b_proc.returncode != 0

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-status", "example-owner/ignore-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert status_proc.stdout.splitlines() == [f"{path_a}\tdirty"]

    off_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-dirty-off", "example-owner/ignore-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert off_proc.returncode == 0, off_proc.stderr

    get_a_proc = subprocess.run(
        ["git", "config", "--local", "--get", f"{section_a}.ignore"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert get_a_proc.returncode != 0
