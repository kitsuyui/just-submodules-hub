from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_open_repo_dispatches_to_code_for_vscode(tmp_path: Path, hub_repo: Path) -> None:
    target_repo = hub_repo / "repo/github.com/acme/example"
    target_repo.mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "open.log"
    write_executable(
        bin_dir / "code",
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$OPEN_LOG\"\n",
    )

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "open-repo", "vscode", "acme/example"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "OPEN_LOG": str(log_file)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert log_file.read_text(encoding="utf-8").strip() == str(target_repo.resolve())


def test_open_repo_resolves_unique_short_name(tmp_path: Path, hub_repo: Path) -> None:
    target_repo = hub_repo / "repo/github.com/acme/example"
    target_repo.mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "open.log"
    write_executable(
        bin_dir / "code",
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$OPEN_LOG\"\n",
    )

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "open-repo", "vscode", "example"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "OPEN_LOG": str(log_file)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert log_file.read_text(encoding="utf-8").strip() == str(target_repo.resolve())


def test_open_repo_dispatches_to_open_for_codex(tmp_path: Path, hub_repo: Path) -> None:
    target_repo = hub_repo / "repo/github.com/acme/example"
    target_repo.mkdir(parents=True)
    bin_dir = tmp_path / "bin"
    log_file = tmp_path / "open.log"
    write_executable(
        bin_dir / "open",
        "#!/bin/sh\nprintf '%s\\n' \"$@\" > \"$OPEN_LOG\"\n",
    )

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "open-repo", "codex", "repo/github.com/acme/example"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "OPEN_LOG": str(log_file)},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert log_file.read_text(encoding="utf-8").splitlines() == ["-a", "Codex", str(target_repo.resolve())]
