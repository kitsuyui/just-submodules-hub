repo_worktrees_branches_source_dir := source_directory()

# Delete local and remote branches in the root repository and managed submodules when their pull requests are already merged.
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_worktrees_branches_source_dir}}/../../../scripts/repo/run-with-hooks.sh" cleanup-worktree-branches {{ARGS}}
