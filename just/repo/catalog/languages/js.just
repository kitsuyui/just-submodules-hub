repo_catalog_languages_js_source_dir := source_directory()

# List submodules that contain a JavaScript or TypeScript project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_js_source_dir}}/../../../../scripts/submodules/list-by-file.sh" package.json
