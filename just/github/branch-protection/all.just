github_branch_protection_all_source_dir := source_directory()

mod classic "all/classic.just"
mod rulesets "all/rulesets.just"

# Show branch protection status for all managed repositories (VISIBILITY: public/private/all).
status VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_all_source_dir}}/../../../scripts/github/default-branch-baseline-bulk.sh" status-all "{{VISIBILITY}}"

# Create or update the managed baseline branch protection for all managed repositories.
apply VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_all_source_dir}}/../../../scripts/github/default-branch-baseline-bulk.sh" apply-all "{{VISIBILITY}}"
