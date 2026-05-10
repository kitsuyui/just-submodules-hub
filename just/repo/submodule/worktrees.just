repo_submodule_worktrees_source_dir := source_directory()

# Reconcile worktrees [scope: all submodules].
reconcile +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_worktrees_source_dir}}/../../../scripts/repo/run-with-hooks.sh" reconcile-submodule-worktrees {{ARGS}}
