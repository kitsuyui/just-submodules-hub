from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from just_submodules_hub.run_action.registry import action

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "reconcile_submodule_worktrees.py"


def _run(mode_args: list[str], extra_args: list[str]) -> int:
    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        str(_SCRIPT),
        *mode_args,
        *extra_args,
    ]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


@action("reconcile-submodule-worktree")
def reconcile_submodule_worktree(args: list[str]) -> int:
    # Equivalent to: reconcile_submodule_worktrees.py one <repo> [args...]
    if not args or not args[0]:
        print("REPO is required", file=sys.stderr)
        return 2
    repo = args[0]
    rest = args[1:]
    return _run(["one", repo], rest)


@action("reconcile-submodule-worktrees")
def reconcile_submodule_worktrees(args: list[str]) -> int:
    # Equivalent to: reconcile_submodule_worktrees.py all [args...]
    return _run(["all"], args)


@action("reconcile-worktrees")
def reconcile_worktrees(args: list[str]) -> int:
    # Equivalent to: reconcile_submodule_worktrees.py root-and-all [args...]
    return _run(["root-and-all"], args)
