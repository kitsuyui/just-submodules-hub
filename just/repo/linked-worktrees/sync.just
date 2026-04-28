repo_linked_worktrees_sync_source_dir := source_directory()

# Plan safe synchronization decisions for Git linked worktrees.
plan +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_sync_source_dir}}/../../../scripts/repo/run-with-hooks.sh" plan-linked-worktree-sync {{ARGS}}
