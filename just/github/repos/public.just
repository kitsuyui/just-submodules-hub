github_repos_public_source_dir := source_directory()

# Create a new public GitHub repository and add it as a submodule (REPO format: owner/name).
create REPO:
  #!/bin/sh
  set -eu
  cd "{{invocation_directory()}}"
  runner="{{github_repos_public_source_dir}}/../../../scripts/repo/run-with-hooks.sh"
  "$runner" create-public-repo "{{REPO}}"
  "$runner" add-repo "https://github.com/{{REPO}}"
