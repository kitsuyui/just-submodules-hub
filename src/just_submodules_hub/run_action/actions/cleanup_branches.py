"""Action handlers for cleaning up merged branches."""

from __future__ import annotations

import subprocess
from pathlib import Path

from just_submodules_hub.run_action.registry import action

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "cleanup_merged_branches.py"


def _run(mode: str, extra_args: list[str]) -> int:
    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        str(_SCRIPT),
        mode,
        *extra_args,
    ]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


@action("cleanup-branches")
def cleanup_branches(args: list[str]) -> int:
    """Clean up merged branches for a single repository."""
    # Equivalent to: cleanup_merged_branches.py one [args...]
    return _run("one", args)


@action("cleanup-submodule-branches")
def cleanup_submodule_branches(args: list[str]) -> int:
    """Clean up merged branches across all submodule repositories."""
    # Equivalent to: cleanup_merged_branches.py all [args...]
    return _run("all", args)


@action("cleanup-worktree-branches")
def cleanup_worktree_branches(args: list[str]) -> int:
    """Clean up merged branches in the root repo and all linked worktrees."""
    # Equivalent to: cleanup_merged_branches.py root-and-all [args...]
    return _run("root-and-all", args)
