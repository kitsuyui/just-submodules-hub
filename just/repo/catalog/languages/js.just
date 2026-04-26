repo_catalog_languages_js_source_dir := source_directory()

# List submodules that contain a JavaScript or TypeScript project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_js_source_dir}}/../../../../scripts/submodules/list-by-file.sh" package.json

# Run a command for each JavaScript or TypeScript submodule.
every COMMAND +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_js_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" every-repo --marker-file package.json {{quote(COMMAND)}} {{ARGS}}
