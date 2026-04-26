github_branch_protection_classic_source_dir := source_directory()

# Show classic branch protection status for the default branch and whether it is redundant.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_classic_source_dir}}/../../../scripts/github/default-branch-ruleset.sh" classic-status "{{REPO}}"

# Delete classic branch protection only when remaining effective rules already cover it.
cleanup REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_classic_source_dir}}/../../../scripts/github/default-branch-ruleset.sh" classic-delete-if-redundant "{{REPO}}"
