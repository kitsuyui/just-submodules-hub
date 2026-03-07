repo_hub_root := "repo/github.com/kitsuyui/just-submodules-hub"

# Add a submodule
add-repo REPO_URL:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" add-repo "{{REPO_URL}}"

# Remove a submodule
remove-repo REPO_PATH:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" remove-repo "{{REPO_PATH}}"

# Create a new public GitHub repository and add it as a submodule (REPO format: owner/name)
create-public-repo REPO:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" create-public-repo "{{REPO}}"

# Create a new private GitHub repository and add it as a submodule (REPO format: owner/name)
create-private-repo REPO:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" create-private-repo "{{REPO}}"

# Update a submodule
update-repo REPO_PATH:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" update-repo "{{REPO_PATH}}"

# Update all submodules
update-all-repo:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" update-all-repo

# Run a command for each submodule
every-repo COMMAND:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" every-repo "{{COMMAND}}"

# Run git grep including submodules
grep +ARGS:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" grep {{ARGS}}

# List repositories for an owner (VISIBILITY: public/private/internal/all)
list-github-repos-owner OWNER VISIBILITY=default_visibility:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" list-github-repos-owner "{{OWNER}}" "{{VISIBILITY}}"

# List repositories for owners (comma- or space-separated)
list-github-repos OWNERS=default_owners VISIBILITY=default_visibility:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" list-github-repos "{{OWNERS}}" "{{VISIBILITY}}"

# List submodules managed by this repository
list-managed-repos:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" list-managed-repos

# List unmanaged repositories among the target owners
list-unmanaged-repos OWNERS=default_owners VISIBILITY=default_visibility:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" list-unmanaged-repos "{{OWNERS}}" "{{VISIBILITY}}"
