# List submodules that contain a Python project marker.
list-repo-python:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/submodules/list-by-file.sh" pyproject.toml

# List submodules that contain a JavaScript or TypeScript project marker.
list-repo-js:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/submodules/list-by-file.sh" package.json

# List submodules that contain a Go project marker.
list-repo-go:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/submodules/list-by-file.sh" go.mod

# List submodules that contain a Rust project marker.
list-repo-rust:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/submodules/list-by-file.sh" Cargo.toml

# List duplicated basenames across tracked files in recursive submodules.
list-duplicate-filenames:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/submodules/list-duplicate-filenames.sh"
