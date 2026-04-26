repo_submodule_default_branch_source_dir := source_directory()

# Sync one repository to its default branch.
sync REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_default_branch_source_dir}}/../../../scripts/repo/run-with-hooks.sh" sync-repo-default-branch "{{REPO}}"

# Sync all repositories to their default branches.
sync-all +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_default_branch_source_dir}}/../../../scripts/repo/run-with-hooks.sh" sync-all-repo-default-branch {{ARGS}}
