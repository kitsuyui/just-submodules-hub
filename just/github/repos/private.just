github_repos_private_source_dir := source_directory()

# Create a new private GitHub repository and add it as a submodule (REPO format: owner/name).
create REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_private_source_dir}}/../../../scripts/repo/run-with-hooks.sh" create-private-repo "{{REPO}}"
