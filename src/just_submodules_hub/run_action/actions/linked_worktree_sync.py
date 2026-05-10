"""Action handlers for listing, planning, and applying linked-worktree syncs."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from just_submodules_hub.run_action.registry import action

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_LIST_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "list_linked_worktrees.py"
_PLAN_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "plan_linked_worktree_sync.py"
_APPLY_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "apply_linked_worktree_sync.py"


def _run_script(script: Path, args: list[str], pass_stdin: bool = False) -> int:
    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        str(script),
        *args,
    ]
    proc = subprocess.run(
        cmd,
        check=False,
        stdin=sys.stdin if pass_stdin else None,
    )
    return proc.returncode


@action("list-linked-worktrees")
def list_linked_worktrees(args: list[str]) -> int:
    """List all linked worktrees registered in the hub."""
    return _run_script(_LIST_SCRIPT, args)


@action("plan-linked-worktree-sync")
def plan_linked_worktree_sync(args: list[str]) -> int:
    """Generate a sync plan for linked worktrees without applying it."""
    return _run_script(_PLAN_SCRIPT, args)


@action("apply-linked-worktree-sync")
def apply_linked_worktree_sync(args: list[str]) -> int:
    """Apply a linked-worktree sync plan, reading from stdin when requested."""
    # Pass stdin through so --from-plan-stdin can read a plan from a pipe
    return _run_script(_APPLY_SCRIPT, args, pass_stdin=True)
