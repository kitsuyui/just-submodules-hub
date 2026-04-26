module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

repo_submodule_unmanaged_source_dir := source_directory()

# List unmanaged repositories among the target owners.
list OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_unmanaged_source_dir}}/../../../scripts/repo/run-with-hooks.sh" list-unmanaged-repos "{{OWNERS}}" "{{VISIBILITY}}"
