repo_submodule_worktrees_source_dir := source_directory()

# Reconcile all managed submodule worktrees and aggregate the result.
reconcile +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_worktrees_source_dir}}/../../../scripts/repo/run-with-hooks.sh" reconcile-submodule-worktrees {{ARGS}}
