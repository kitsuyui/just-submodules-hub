module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

github_repos_source_dir := source_directory()

mod owner "repos/owner.just"
mod private "repos/private.just"
mod public "repos/public.just"

# Deprecated compatibility aliases. Prefer the canonical namespace/resource/verb commands.
alias create-public := public::create
alias create-private := private::create
alias list-owner := owner::list

# List repositories for owners (comma- or space-separated).
list OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-github-repos "{{OWNERS}}" "{{VISIBILITY}}"
