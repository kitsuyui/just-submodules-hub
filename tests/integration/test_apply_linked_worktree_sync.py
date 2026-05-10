from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_apply_linked_worktree_sync_routes_planned_actions(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    feature = tmp_path / "repo-feature"
    feature.mkdir()

    calls_file = tmp_path / "git-calls.txt"
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "git",
        f"""#!/bin/sh
printf '%s|%s\\n' "$PWD" "$*" >> "{calls_file}"
case "$*" in
  "-C {repo} symbolic-ref --short refs/remotes/origin/HEAD")
    printf '%s\\n' origin/main
    exit 0
    ;;
  "-C {repo} worktree list --porcelain")
    printf '%s\\n' "worktree {repo}" "HEAD 1111111111111111111111111111111111111111" "branch refs/heads/main" ""
    printf '%s\\n' "worktree {feature}" "HEAD 2222222222222222222222222222222222222222" "branch refs/heads/feature/test" ""
    exit 0
    ;;
  "-C {repo} status --porcelain"|"-C {feature} status --porcelain")
    exit 0
    ;;
  "-C {repo} rev-parse HEAD")
    printf '%s\\n' 1111111111111111111111111111111111111111
    exit 0
    ;;
  "-C {feature} rev-parse HEAD")
    printf '%s\\n' 2222222222222222222222222222222222222222
    exit 0
    ;;
  "-C {feature} log --format=%H origin/main..feature/test --")
    printf '%s\\n' 2222222222222222222222222222222222222222
    exit 0
    ;;
  "-C {feature} rev-parse --verify --quiet refs/remotes/origin/feature/test")
    printf '%s\\n' 2222222222222222222222222222222222222222
    exit 0
    ;;
  "-C {repo} fetch origin main"|"-C {feature} fetch origin feature/test")
    exit 0
    ;;
  "-C {repo} merge --ff-only origin/main"|"-C {feature} rebase origin/feature/test")
    exit 0
    ;;
esac
exit 1
""",
    )
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
printf '%s\\n' "no pull requests found for branch" >&2
exit 1
""",
    )

    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [str(RUN_ACTION_SCRIPT), "apply-linked-worktree-sync", "--format", "jsonl"],
        cwd=str(repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert [json.loads(line) for line in proc.stdout.splitlines()] == [
        {
            "action": "pull-default",
            "branch": "main",
            "dirty": "clean",
            "draft": "",
            "message": "already up to date",
            "path": str(repo),
            "pr": "",
            "status": "noop",
            "target": "origin/main",
        },
        {
            "action": "rebase-branch",
            "branch": "feature/test",
            "dirty": "clean",
            "draft": "",
            "message": "already up to date",
            "path": str(feature),
            "pr": "",
            "status": "noop",
            "target": "origin/feature/test",
        },
    ]
