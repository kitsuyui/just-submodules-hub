repo_submodule_managed_source_dir := source_directory()
module_default_visibility := "all"

# List submodules managed by this repository.
list OWNERS="" VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_managed_source_dir}}/../../../scripts/repo/run-with-hooks.sh" list-managed-repos "{{OWNERS}}" "{{VISIBILITY}}"
