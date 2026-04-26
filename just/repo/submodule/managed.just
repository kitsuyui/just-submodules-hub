repo_submodule_managed_source_dir := source_directory()

# List submodules managed by this repository.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_managed_source_dir}}/../../../scripts/repo/run-with-hooks.sh" list-managed-repos
