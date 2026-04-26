repo_catalog_languages_python_source_dir := source_directory()

# List submodules that contain a Python project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_python_source_dir}}/../../../../scripts/submodules/list-by-file.sh" pyproject.toml
