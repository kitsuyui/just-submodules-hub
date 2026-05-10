from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_add_repo_records_shallow_recommendation(tmp_path: Path) -> None:
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
        [
            str(RUN_ACTION_SCRIPT),
            "add-repo",
            "https://github.com/example-owner/example-repo",
        ],
        cwd=str(hub_repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    calls = calls_file.read_text(encoding="utf-8").splitlines()
    assert calls == [
        "submodule add -- git@github.com:example-owner/example-repo.git repo/github.com/example-owner/example-repo",
        "config -f .gitmodules submodule.repo/github.com/example-owner/example-repo.shallow true",
        "config --local submodule.repo/github.com/example-owner/example-repo.ignore all",
    ]
