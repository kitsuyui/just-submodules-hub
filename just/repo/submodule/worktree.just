repo_submodule_worktree_source_dir := source_directory()

# Reconcile one managed submodule worktree.
reconcile REPO FORMAT="table":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_worktree_source_dir}}/../../../scripts/repo/run-with-hooks.sh" reconcile-submodule-worktree "{{REPO}}" --format "{{FORMAT}}"
