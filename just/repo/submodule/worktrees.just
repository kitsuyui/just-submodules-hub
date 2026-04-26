repo_submodule_worktrees_source_dir := source_directory()

# Reconcile all managed submodule worktrees and aggregate the result.
reconcile FORMAT="table" JOBS="4":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_worktrees_source_dir}}/../../../scripts/repo/run-with-hooks.sh" reconcile-submodule-worktrees --format "{{FORMAT}}" --jobs "{{JOBS}}"
