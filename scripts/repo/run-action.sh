#!/bin/sh
set -eu

action="${1:-}"
if [ -z "$action" ]; then
  echo "action is required" >&2
  exit 2
fi
shift
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH='' cd -- "$script_dir/../.." && pwd)

# Actions migrated to the Python entrypoint (#60 item 3, phases 1-3c).
case "$action" in
  list-github-repos-owner|list-github-repos|list-managed-repos|list-unmanaged-repos|open-repo|every-repo|grep|\
init-all-repos|sync-repo-default-branch|sync-all-repo-default-branch|reconcile-submodule-worktree|reconcile-submodule-worktrees|reconcile-worktrees|cleanup-branches|cleanup-submodule-branches|cleanup-worktree-branches|\
add-repo|remove-repo|create-public-repo|create-private-repo|commit-submodule-pointers|list-linked-worktrees|plan-linked-worktree-sync|apply-linked-worktree-sync|\
add-linked-worktree|remove-linked-worktree|install-linked-worktree-hooks|reset-linked-worktree|cleanup-linked-worktrees|\
submodule-root-status-hide|submodule-root-status-show|submodule-root-status-visibility|\
submodule-hide-root-status-changes|submodule-hide-worktree-changes|submodule-hide-all-changes|submodule-ignore-all-on|\
submodule-show-root-status-changes|submodule-show-worktree-changes|submodule-show-all-changes|submodule-ignore-all-off|\
submodule-root-status-changes-visibility|submodule-worktree-changes-visibility|submodule-all-changes-visibility|\
submodule-ignore-dirty-on|submodule-ignore-dirty-off|submodule-ignore-dirty-status|\
submodule-ignore-all-status)
    exec uv run --project "$project_root" env PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" python -m just_submodules_hub.run_action "$action" "$@"
    ;;
esac

echo "Unknown action: $action" >&2
exit 2
