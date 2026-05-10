repo_submodule_branches_source_dir := source_directory()

# Delete merged branches [scope: all submodules].
cleanup +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_branches_source_dir}}/../../../scripts/repo/run-with-hooks.sh" cleanup-submodule-branches {{ARGS}}
