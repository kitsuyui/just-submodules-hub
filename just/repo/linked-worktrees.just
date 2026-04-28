repo_linked_worktrees_source_dir := source_directory()

mod hooks "linked-worktrees/hooks.just"
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

# Plan or apply a reset of one Git linked worktree branch to its target.
reset PATH +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" reset-linked-worktree "{{PATH}}" {{ARGS}}

# Plan or apply cleanup of safe Git linked worktree candidates.
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" cleanup-linked-worktrees {{ARGS}}
