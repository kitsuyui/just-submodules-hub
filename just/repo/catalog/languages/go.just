repo_catalog_languages_go_source_dir := source_directory()

# List submodules that contain a Go project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_go_source_dir}}/../../../../scripts/submodules/list-by-file.sh" go.mod

# Run a command for each Go submodule.
every COMMAND +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_go_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" every-repo --marker-file go.mod {{quote(COMMAND)}} {{ARGS}}
