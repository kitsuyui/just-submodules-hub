module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

repo_submodule_source_dir := source_directory()

# Add a submodule.
add REPO_URL:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" add-repo "{{REPO_URL}}"

# Remove a submodule.
remove REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" remove-repo "{{REPO}}"

# Sync one repository to its default branch.
sync-default-branch REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" sync-repo-default-branch "{{REPO}}"

# Sync all repositories to their default branches.
sync-all-default-branch:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" sync-all-repo-default-branch

# Commit only submodule pointer changes in the parent repository.
commit-pointers MESSAGE="Update submodule pointers":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" commit-submodule-pointers "{{MESSAGE}}"

# Enable local ignore=dirty for all managed submodules.
ignore-dirty-on:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-on

# Disable local ignore=dirty for all managed submodules.
ignore-dirty-off:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-off

# Show local ignore=dirty status for all managed submodules.
ignore-dirty-status:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-status

# Run a command for each submodule.
every COMMAND:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" every-repo "{{COMMAND}}"

# Run git grep including submodules.
grep +ARGS:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" grep {{ARGS}}

# List submodules managed by this repository.
list-managed:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-managed-repos

# List unmanaged repositories among the target owners.
list-unmanaged OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-unmanaged-repos "{{OWNERS}}" "{{VISIBILITY}}"
