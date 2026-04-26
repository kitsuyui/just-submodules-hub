repo_catalog_duplicates_filenames_source_dir := source_directory()

# List duplicated basenames across tracked files in recursive submodules.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_duplicates_filenames_source_dir}}/../../../../scripts/submodules/list-duplicate-filenames.sh"
