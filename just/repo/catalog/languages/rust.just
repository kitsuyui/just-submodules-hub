repo_catalog_languages_rust_source_dir := source_directory()

# List submodules that contain a Rust project marker.
list:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_rust_source_dir}}/../../../../scripts/submodules/list-by-file.sh" Cargo.toml

# Run a command for each Rust submodule.
every COMMAND +ARGS="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_catalog_languages_rust_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" every-repo --marker-file Cargo.toml {{quote(COMMAND)}} {{ARGS}}
