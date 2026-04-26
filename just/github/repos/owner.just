module_default_visibility := "all"

github_repos_owner_source_dir := source_directory()

# List repositories for an owner (VISIBILITY: public/private/internal/all).
list OWNER VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_owner_source_dir}}/../../../scripts/repo/run-with-hooks.sh" list-github-repos-owner "{{OWNER}}" "{{VISIBILITY}}"
