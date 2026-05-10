from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_list_linked_worktrees_routes_to_git_worktree_list(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s\\n' "$*" >> "{calls_file}"
if [ "$*" = "worktree list --porcelain" ]; then
  printf '%s\\n' "worktree {repo}" "HEAD 1111111111111111111111111111111111111111" "branch refs/heads/main" ""
  printf '%s\\n' "worktree {repo}-linked" "HEAD 2222222222222222222222222222222222222222" "detached" ""
  exit 0
fi
exit 1
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "list-linked-worktrees", "--format", "jsonl"],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls_file.read_text(encoding="utf-8").splitlines() == [
        "worktree list --porcelain",
    ]
    assert [json.loads(line) for line in proc.stdout.splitlines()] == [
        {
            "branch": "main",
            "detached": "no",
            "head": "1111111111111111111111111111111111111111",
            "locked": "no",
            "message": "",
            "path": str(repo),
            "prunable": "no",
        },
        {
            "branch": "",
            "detached": "yes",
            "head": "2222222222222222222222222222222222222222",
            "locked": "no",
            "message": "",
            "path": f"{repo}-linked",
            "prunable": "no",
        },
    ]
