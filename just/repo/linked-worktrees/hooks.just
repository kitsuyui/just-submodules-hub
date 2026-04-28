repo_linked_worktrees_hooks_source_dir := source_directory()

# Install linked worktree safety hooks for the parent repository.
install +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_linked_worktrees_hooks_source_dir}}/../../../scripts/repo/run-with-hooks.sh" install-linked-worktree-hooks {{ARGS}}
