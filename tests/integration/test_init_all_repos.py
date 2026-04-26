from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_init_all_repos_uses_explicit_jobs(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    hub_repo.mkdir()

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s\\n' "$*" >> "{calls_file}"
exit 0
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "init-all-repos", "4"],
        cwd=str(hub_repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        "-c protocol.file.allow=always submodule update --init --recursive --recommend-shallow --jobs 4",
        "config -f .gitmodules --name-only --get-regexp ^submodule\\..*\\.path$",
    ]


def test_init_all_repos_uses_submodule_fetch_jobs_config(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    hub_repo.mkdir()

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s\\n' "$*" >> "{calls_file}"
if [ "$*" = "config --get submodule.fetchJobs" ]; then
  printf '%s\\n' 6
fi
exit 0
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "init-all-repos", ""],
        cwd=str(hub_repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        "config --get submodule.fetchJobs",
        "-c protocol.file.allow=always submodule update --init --recursive --recommend-shallow --jobs 6",
        "config -f .gitmodules --name-only --get-regexp ^submodule\\..*\\.path$",
    ]
