module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

repo_submodule_source_dir := source_directory()

mod default-branch "submodule/default-branch.just"
mod managed "submodule/managed.just"
mod pointers "submodule/pointers.just"
mod root-status "submodule/root-status.just"
mod unmanaged "submodule/unmanaged.just"

# Add a submodule.
add REPO_URL:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" add-repo "{{REPO_URL}}"

# Remove a submodule.
remove REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" remove-repo "{{REPO}}"

# Initialize all registered submodules.
init-all JOBS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" init-all-repos "{{JOBS}}"

# Deprecated alias for default-branch::sync.
sync-default-branch REPO:
  #!/bin/sh
  echo "warning: repo::submodule::sync-default-branch is deprecated; use repo::submodule::default-branch::sync" >&2
  cd "{{invocation_directory()}}" && just repo submodule default-branch sync "{{REPO}}"

# Deprecated alias for default-branch::sync-all.
sync-all-default-branch:
  #!/bin/sh
  echo "warning: repo::submodule::sync-all-default-branch is deprecated; use repo::submodule::default-branch::sync-all" >&2
  cd "{{invocation_directory()}}" && just repo submodule default-branch sync-all

# Deprecated alias for pointers::commit.
commit-pointers MESSAGE="Update submodule pointers":
  #!/bin/sh
  echo "warning: repo::submodule::commit-pointers is deprecated; use repo::submodule::pointers::commit" >&2
  cd "{{invocation_directory()}}" && just repo submodule pointers commit "{{MESSAGE}}"

# Deprecated alias for root-status::hide.
hide-root-status-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-hide-root-status-changes "{{REPO}}"

# Deprecated alias for root-status::show.
show-root-status-changes REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" submodule-show-root-status-changes "{{REPO}}"

# Deprecated alias for root-status::visibility.
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

# Deprecated alias for managed::list.
list-managed:
  #!/bin/sh
  echo "warning: repo::submodule::list-managed is deprecated; use repo::submodule::managed::list" >&2
  cd "{{invocation_directory()}}" && just repo submodule managed list

# Deprecated alias for unmanaged::list.
list-unmanaged OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  echo "warning: repo::submodule::list-unmanaged is deprecated; use repo::submodule::unmanaged::list" >&2
  cd "{{invocation_directory()}}" && just repo submodule unmanaged list "{{OWNERS}}" "{{VISIBILITY}}"
