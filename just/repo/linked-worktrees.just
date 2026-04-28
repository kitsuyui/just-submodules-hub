repo_linked_worktrees_source_dir := source_directory()

# List Git linked worktrees for the parent repository.
list +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-linked-worktrees {{ARGS}}
