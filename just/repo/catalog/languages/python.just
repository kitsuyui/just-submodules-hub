repo_catalog_languages_python_source_dir := source_directory()

# List submodules that contain a Python project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_python_source_dir}}/../../../../scripts/submodules/list-by-file.sh" pyproject.toml

# Run a command for each Python submodule.
every COMMAND +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_python_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" every-repo --marker-file pyproject.toml {{quote(COMMAND)}} {{ARGS}}
