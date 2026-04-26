repo_worktrees_source_dir := source_directory()

mod branches "worktrees/branches.just"

# Reconcile the root repository and all managed submodule worktrees.
reconcile +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" reconcile-worktrees {{ARGS}}
