repo_branches_source_dir := source_directory()

# Delete local and remote branches in the root repository when their pull requests are already merged.
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_branches_source_dir}}/../../scripts/repo/run-with-hooks.sh" cleanup-branches {{ARGS}}
