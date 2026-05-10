"""Action handlers for reconciling submodule worktrees."""

from __future__ import annotations

import sys

from just_submodules_hub.run_action.registry import action
from just_submodules_hub.submodule_worktree_reconcile import main as reconcile_main


@action("reconcile-submodule-worktree")
def reconcile_submodule_worktree(args: list[str]) -> int:
    """Reconcile the linked worktree for a single submodule repository."""
    if not args or not args[0]:
        print("REPO is required", file=sys.stderr)
        return 2
    repo = args[0]
    rest = args[1:]
    return reconcile_main(["one", repo, *rest])


@action("reconcile-submodule-worktrees")
def reconcile_submodule_worktrees(args: list[str]) -> int:
    """Reconcile linked worktrees for all submodule repositories."""
    return reconcile_main(["all", *args])


@action("reconcile-worktrees")
def reconcile_worktrees(args: list[str]) -> int:
    """Reconcile linked worktrees for the root repo and all submodules."""
    return reconcile_main(["root-and-all", *args])
