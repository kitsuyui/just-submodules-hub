repo_catalog_source_dir := source_directory()

# List submodules that contain a Python project marker.
python:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_source_dir}}/../../scripts/submodules/list-by-file.sh" pyproject.toml

# List submodules that contain a JavaScript or TypeScript project marker.
js:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_source_dir}}/../../scripts/submodules/list-by-file.sh" package.json

# List submodules that contain a Go project marker.
go:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_source_dir}}/../../scripts/submodules/list-by-file.sh" go.mod

# List submodules that contain a Rust project marker.
rust:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_source_dir}}/../../scripts/submodules/list-by-file.sh" Cargo.toml

# List duplicated basenames across tracked files in recursive submodules.
duplicate-filenames:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_source_dir}}/../../scripts/submodules/list-duplicate-filenames.sh"
