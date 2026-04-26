repo_catalog_languages_go_source_dir := source_directory()

# List submodules that contain a Go project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_go_source_dir}}/../../../../scripts/submodules/list-by-file.sh" go.mod
