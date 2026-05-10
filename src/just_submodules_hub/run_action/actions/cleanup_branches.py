"""Action handlers for cleaning up merged branches."""

from __future__ import annotations

from just_submodules_hub.branch_cleanup import main as cleanup_main
from just_submodules_hub.run_action.registry import action


@action("cleanup-branches")
def cleanup_branches(args: list[str]) -> int:
    """Clean up merged branches for a single repository."""
    return cleanup_main(["one", *args])


@action("cleanup-submodule-branches")
def cleanup_submodule_branches(args: list[str]) -> int:
    """Clean up merged branches across all submodule repositories."""
    return cleanup_main(["all", *args])


@action("cleanup-worktree-branches")
def cleanup_worktree_branches(args: list[str]) -> int:
    """Clean up merged branches in the root repo and all submodule repositories.

    The action name and the matching ``repo::worktrees::branches::cleanup``
    recipe use ``worktrees`` in the loose sense of "all working trees managed
    by this hub" — that is, the root repository plus every submodule. It does
    not target Git linked worktrees (``git worktree add`` paths).
    """
    return cleanup_main(["root-and-all", *args])
