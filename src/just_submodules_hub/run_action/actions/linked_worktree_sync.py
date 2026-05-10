"""Action handlers for listing, planning, and applying linked-worktree syncs."""

from __future__ import annotations

from just_submodules_hub.linked_worktree_apply import main as apply_main
from just_submodules_hub.linked_worktree_inventory import main as list_main
from just_submodules_hub.linked_worktree_planning import main as plan_main
from just_submodules_hub.run_action.registry import action


@action("list-linked-worktrees")
def list_linked_worktrees(args: list[str]) -> int:
    """List all linked worktrees registered in the hub."""
    return list_main(args)


@action("plan-linked-worktree-sync")
def plan_linked_worktree_sync(args: list[str]) -> int:
    """Generate a sync plan for linked worktrees without applying it."""
    return plan_main(args)


@action("apply-linked-worktree-sync")
def apply_linked_worktree_sync(args: list[str]) -> int:
    """Apply a linked-worktree sync plan, reading from stdin when requested.

    stdin is shared with the parent process, so --from-plan-stdin piping works
    without any special handling.
    """
    return apply_main(args)
