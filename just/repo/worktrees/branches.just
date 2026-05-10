repo_worktrees_branches_source_dir := source_directory()

# Delete merged branches [scope: root + all submodules].
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_worktrees_branches_source_dir}}/../../../scripts/repo/run-with-hooks.sh" cleanup-worktree-branches {{ARGS}}
