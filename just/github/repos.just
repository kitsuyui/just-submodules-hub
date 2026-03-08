module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

github_repos_source_dir := source_directory()

# Create a new public GitHub repository and add it as a submodule (REPO format: owner/name).
create-public REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" create-public-repo "{{REPO}}"

# Create a new private GitHub repository and add it as a submodule (REPO format: owner/name).
create-private REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" create-private-repo "{{REPO}}"

# List repositories for an owner (VISIBILITY: public/private/internal/all).
list-owner OWNER VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-github-repos-owner "{{OWNER}}" "{{VISIBILITY}}"

# List repositories for owners (comma- or space-separated).
list OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-github-repos "{{OWNERS}}" "{{VISIBILITY}}"
