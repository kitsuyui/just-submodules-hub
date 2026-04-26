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

# Hide all submodule changes from the parent repository status.
hide-root-status-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-hide-root-status-changes "{{REPO}}"

# Show submodule changes in the parent repository status again.
show-root-status-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-show-root-status-changes "{{REPO}}"

# Show whether submodule changes are hidden from the parent repository status.
root-status-changes-visibility REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-root-status-changes-visibility "{{REPO}}"

# Deprecated alias for hide-root-status-changes.
hide-worktree-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-hide-worktree-changes "{{REPO}}"

# Deprecated alias for show-root-status-changes.
show-worktree-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-show-worktree-changes "{{REPO}}"

# Deprecated alias for root-status-changes-visibility.
worktree-changes-visibility REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-worktree-changes-visibility "{{REPO}}"

# Deprecated alias for hide-worktree-changes.
ignore-dirty-on REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-on "{{REPO}}"

# Deprecated alias for show-worktree-changes.
ignore-dirty-off REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-off "{{REPO}}"

# Deprecated alias for worktree-changes-visibility.
ignore-dirty-status REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-dirty-status "{{REPO}}"

# Deprecated alias for hide-root-status-changes.
hide-all-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-hide-all-changes "{{REPO}}"

# Deprecated alias for show-root-status-changes.
show-all-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-show-all-changes "{{REPO}}"

# Deprecated alias for root-status-changes-visibility.
all-changes-visibility REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-all-changes-visibility "{{REPO}}"

# Deprecated alias for hide-all-changes.
ignore-all-on REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-all-on "{{REPO}}"

# Deprecated alias for show-all-changes.
ignore-all-off REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-all-off "{{REPO}}"

# Deprecated alias for all-changes-visibility.
ignore-all-status REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-ignore-all-status "{{REPO}}"

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
