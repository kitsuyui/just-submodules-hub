"""Side-effect imports that register all action handlers."""

from just_submodules_hub.run_action.actions import (  # noqa: F401
    add_repo,
    cleanup_branches,
    commit_submodule_pointers,
    create_repo,
    every_repo,
    grep,
    init_all_repos,
    linked_worktree_sync,
    linked_worktrees,
    list_github_repos,
    list_managed_repos,
    list_unmanaged_repos,
    open_repo,
    reconcile_worktrees,
    remove_repo,
    submodule_deprecated_aliases,
    submodule_root_status,
    sync_repo_default_branch,
)
