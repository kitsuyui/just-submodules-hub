module_default_owners := "kitsuyui,gitignore-in"
module_default_visibility := "all"

github_repos_source_dir := source_directory()

mod owner "repos/owner.just"
mod private "repos/private.just"
mod public "repos/public.just"

# Deprecated alias for public::create.
create-public REPO:
  #!/bin/sh
  echo "warning: github::repos::create-public is deprecated; use github::repos::public::create" >&2
  cd "{{invocation_directory()}}" && just github repos public create "{{REPO}}"

# Deprecated alias for private::create.
create-private REPO:
  #!/bin/sh
  echo "warning: github::repos::create-private is deprecated; use github::repos::private::create" >&2
  cd "{{invocation_directory()}}" && just github repos private create "{{REPO}}"

# Deprecated alias for owner::list.
list-owner OWNER VISIBILITY=module_default_visibility:
  #!/bin/sh
  echo "warning: github::repos::list-owner is deprecated; use github::repos::owner::list" >&2
  cd "{{invocation_directory()}}" && just github repos owner list "{{OWNER}}" "{{VISIBILITY}}"

# List repositories for owners (comma- or space-separated).
list OWNERS=module_default_owners VISIBILITY=module_default_visibility:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_repos_source_dir}}/../../scripts/repo/run-with-hooks.sh" list-github-repos "{{OWNERS}}" "{{VISIBILITY}}"
