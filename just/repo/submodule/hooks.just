repo_submodule_hooks_source_dir := source_directory()

# Install configured Git hook managers in all managed submodules.
install +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_hooks_source_dir}}/../../../scripts/repo/run-with-hooks.sh" install-submodule-hooks {{ARGS}}
