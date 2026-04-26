github_branch_protection_source_dir := source_directory()

mod all "branch-protection/all.just"
mod classic "branch-protection/classic.just"
mod legacy "branch-protection/legacy.just"
mod ruleset "branch-protection/ruleset.just"

# Show baseline branch protection status for one repository default branch.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" status "{{REPO}}"

# Create or update the managed baseline branch protection for one repository default branch.
apply REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" apply "{{REPO}}"

# Deprecated compatibility aliases. Prefer the canonical namespace/resource/verb commands.
alias legacy-status := legacy::status
alias cleanup-ruleset := ruleset::cleanup
alias classic-status := classic::status
alias cleanup-classic := classic::cleanup
alias status-all := all::status
alias apply-all := all::apply
alias cleanup-rulesets-all := all::rulesets::cleanup
alias cleanup-classic-all := all::classic::cleanup
