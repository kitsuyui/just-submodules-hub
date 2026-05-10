repo_worktrees_source_dir := source_directory()

mod branches "worktrees/branches.just"

# Reconcile worktrees [scope: root + all submodules].
reconcile +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" reconcile-worktrees {{ARGS}}
