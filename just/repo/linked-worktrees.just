repo_linked_worktrees_source_dir := source_directory()

mod sync "linked-worktrees/sync.just"

# List Git linked worktrees for the parent repository.
list +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-linked-worktrees {{ARGS}}

# Add a Git linked worktree for the parent repository.
add PATH +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" add-linked-worktree "{{PATH}}" {{ARGS}}

# Remove a Git linked worktree for the parent repository.
remove PATH +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" remove-linked-worktree "{{PATH}}" {{ARGS}}
