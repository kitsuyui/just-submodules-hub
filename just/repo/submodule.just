module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

repo_submodule_source_dir := source_directory()

mod default-branch "submodule/default-branch.just"
mod managed "submodule/managed.just"
mod pointers "submodule/pointers.just"
mod root-status "submodule/root-status.just"
mod unmanaged "submodule/unmanaged.just"
mod worktree "submodule/worktree.just"
mod worktrees "submodule/worktrees.just"

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

# Deprecated compatibility aliases. Prefer the canonical namespace/resource/verb commands.
alias sync-default-branch := default-branch::sync
alias sync-all-default-branch := default-branch::sync-all
alias commit-pointers := pointers::commit
alias hide-root-status-changes := root-status::hide
alias show-root-status-changes := root-status::show
alias root-status-changes-visibility := root-status::visibility
alias hide-worktree-changes := root-status::hide
alias show-worktree-changes := root-status::show
alias worktree-changes-visibility := root-status::visibility
alias ignore-dirty-on := root-status::hide
alias ignore-dirty-off := root-status::show
alias ignore-dirty-status := root-status::visibility
alias hide-all-changes := root-status::hide
alias show-all-changes := root-status::show
alias all-changes-visibility := root-status::visibility
alias ignore-all-on := root-status::hide
alias ignore-all-off := root-status::show
alias ignore-all-status := root-status::visibility

# Run a command for each submodule.
every COMMAND +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" every-repo {{quote(COMMAND)}} {{ARGS}}

# Run git grep including submodules.
grep +ARGS:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_source_dir}}/../../scripts/repo/run-with-hooks.sh" grep {{ARGS}}

alias list-managed := managed::list
alias list-unmanaged := unmanaged::list
