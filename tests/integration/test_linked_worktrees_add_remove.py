from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_add_linked_worktree_initializes_submodules_with_requested_mode(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    linked = tmp_path / "repo-feature"
    linked.mkdir()

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s|%s\\n' "$PWD" "$*" >> "{calls_file}"
exit 0
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [
            str(RUN_ACTION_SCRIPT),
            "add-linked-worktree",
            str(linked),
            "--branch",
            "feature/test",
            "--start-point",
            "main",
            "--fetch-fallback",
            "--jobs",
            "2",
        ],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        f"{repo}|worktree add -b feature/test {linked} main",
        f"{linked}|-c protocol.file.allow=always submodule update --init --recursive --recommend-shallow --force --no-fetch --jobs 2",
        f"{linked}|config -f .gitmodules --name-only --get-regexp ^submodule\\..*\\.path$",
    ]


def test_add_linked_worktree_can_skip_submodule_initialization(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    linked = tmp_path / "repo-feature"

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s|%s\\n' "$PWD" "$*" >> "{calls_file}"
exit 0
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "add-linked-worktree", str(linked), "--no-submodules"],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        f"{repo}|worktree add {linked}",
    ]


def test_remove_linked_worktree_accepts_force(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    linked = tmp_path / "repo-feature"

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s|%s\\n' "$PWD" "$*" >> "{calls_file}"
exit 0
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "remove-linked-worktree", str(linked), "--force"],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        f"{repo}|worktree remove --force {linked}",
    ]
