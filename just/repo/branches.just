repo_branches_source_dir := source_directory()

# Delete merged branches [scope: root only].
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_branches_source_dir}}/../../scripts/repo/run-with-hooks.sh" cleanup-branches {{ARGS}}
