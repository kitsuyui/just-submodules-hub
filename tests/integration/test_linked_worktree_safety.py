from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_install_linked_worktree_hooks_creates_pre_push_hook(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    (repo / ".git" / "hooks").mkdir(parents=True)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
if [ "$*" = "-C {repo} rev-parse --git-common-dir" ]; then
  printf '%s\\n' .git
  exit 0
fi
exit 1
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "install-linked-worktree-hooks", "--format", "jsonl"],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert json.loads(proc.stdout) == {
        "message": "pre-push hook installed",
        "path": str(repo / ".git" / "hooks" / "pre-push"),
        "status": "installed",
    }
    assert "refs/heads/worktree/*" in (repo / ".git" / "hooks" / "pre-push").read_text(
        encoding="utf-8"
    )
