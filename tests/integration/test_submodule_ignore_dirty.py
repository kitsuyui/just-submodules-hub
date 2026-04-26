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


def test_submodule_worktree_visibility_commands_use_hidden_visible_labels(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "hide-me",
        {"README.md": "hello\n"},
    )
    submodule_path = "repo/github.com/example-owner/hide-me"
    section = "submodule.repo/github.com/example-owner/hide-me"
    add_submodule(hub_repo, remote, submodule_path)

    hide_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-hide-worktree-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert hide_proc.returncode == 0, hide_proc.stderr
    assert run(["git", "config", "--local", "--get", f"{section}.ignore"], cwd=hub_repo) == "all"

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-worktree-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert status_proc.stdout.splitlines() == [f"{submodule_path}\thidden"]

    show_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-show-worktree-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert show_proc.returncode == 0, show_proc.stderr

    status_after_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-worktree-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_after_proc.returncode == 0, status_after_proc.stderr
    assert status_after_proc.stdout.splitlines() == [f"{submodule_path}\tvisible"]


def test_submodule_root_status_visibility_commands_use_hidden_visible_labels(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "hide-root-me",
        {"README.md": "hello\n"},
    )
    submodule_path = "repo/github.com/example-owner/hide-root-me"
    section = "submodule.repo/github.com/example-owner/hide-root-me"
    add_submodule(hub_repo, remote, submodule_path)

    hide_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-hide-root-status-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert hide_proc.returncode == 0, hide_proc.stderr
    assert run(["git", "config", "--local", "--get", f"{section}.ignore"], cwd=hub_repo) == "all"

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-root-status-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert status_proc.stdout.splitlines() == [f"{submodule_path}\thidden"]

    show_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-show-root-status-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert show_proc.returncode == 0, show_proc.stderr

    status_after_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-root-status-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_after_proc.returncode == 0, status_after_proc.stderr
    assert status_after_proc.stdout.splitlines() == [f"{submodule_path}\tvisible"]


def test_submodule_ignore_all_toggle_supports_targeted_repo(tmp_path: Path, hub_repo: Path) -> None:
    remote_a = create_remote(
        tmp_path,
        "example-owner",
        "ignore-all-me",
        {"README.md": "hello\n"},
    )
    remote_b = create_remote(
        tmp_path,
        "example-owner",
        "keep-all-visible",
        {"README.md": "world\n"},
    )
    path_a = "repo/github.com/example-owner/ignore-all-me"
    path_b = "repo/github.com/example-owner/keep-all-visible"
    section_a = "submodule.repo/github.com/example-owner/ignore-all-me"
    section_b = "submodule.repo/github.com/example-owner/keep-all-visible"

    add_submodule(hub_repo, remote_a, path_a)
    add_submodule(hub_repo, remote_b, path_b)

    on_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-all-on", "example-owner/ignore-all-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert on_proc.returncode == 0, on_proc.stderr
    assert run(["git", "config", "--local", "--get", f"{section_a}.ignore"], cwd=hub_repo) == "all"

    get_b_proc = subprocess.run(
        ["git", "config", "--local", "--get", f"{section_b}.ignore"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert get_b_proc.returncode != 0

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-all-status", "example-owner/ignore-all-me"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert status_proc.stdout.splitlines() == [f"{path_a}\tall"]

    off_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-ignore-all-off", "example-owner/ignore-all-me"],
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


def test_submodule_all_visibility_commands_use_hidden_visible_labels(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "hide-all-me",
        {"README.md": "hello\n"},
    )
    submodule_path = "repo/github.com/example-owner/hide-all-me"
    add_submodule(hub_repo, remote, submodule_path)

    hide_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-hide-all-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert hide_proc.returncode == 0, hide_proc.stderr

    status_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-all-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_proc.returncode == 0, status_proc.stderr
    assert status_proc.stdout.splitlines() == [f"{submodule_path}\thidden"]

    show_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-show-all-changes"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert show_proc.returncode == 0, show_proc.stderr

    status_after_proc = subprocess.run(
        [str(ACTION_SCRIPT), "submodule-all-changes-visibility"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )
    assert status_after_proc.returncode == 0, status_after_proc.stderr
    assert status_after_proc.stdout.splitlines() == [f"{submodule_path}\tvisible"]
