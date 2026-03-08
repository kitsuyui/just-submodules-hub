github_branch_protection_source_dir := source_directory()

# Show baseline branch protection status for one repository default branch.
status REPO:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" status "{{REPO}}"

# Create or update the managed baseline branch protection for one repository default branch.
apply REPO:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" apply "{{REPO}}"

# Show legacy default-branch rulesets and whether they can be deleted safely.
legacy-status REPO:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" legacy-status "{{REPO}}"

# Delete one redundant legacy ruleset by id or name.
cleanup-ruleset REPO IDENTIFIER:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" delete-if-redundant "{{REPO}}" "{{IDENTIFIER}}"

# Show classic branch protection status for the default branch and whether it is redundant.
classic-status REPO:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" classic-status "{{REPO}}"

# Delete classic branch protection only when remaining effective rules already cover it.
cleanup-classic REPO:
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-ruleset.sh" classic-delete-if-redundant "{{REPO}}"

# Show branch protection status for all managed repositories (VISIBILITY: public/private/all).
status-all VISIBILITY="public":
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-baseline-bulk.sh" status-all "{{VISIBILITY}}"

# Create or update the managed baseline branch protection for all managed repositories.
apply-all VISIBILITY="public":
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-baseline-bulk.sh" apply-all "{{VISIBILITY}}"

# Delete redundant legacy rulesets for all managed repositories and skip manual-review cases.
cleanup-rulesets-all VISIBILITY="public":
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-baseline-bulk.sh" cleanup-rulesets-all "{{VISIBILITY}}"

# Delete redundant classic branch protection for all managed repositories and skip manual-review cases.
cleanup-classic-all VISIBILITY="public":
  #!/bin/sh
  "{{github_branch_protection_source_dir}}/../../scripts/github/default-branch-baseline-bulk.sh" cleanup-classic-all "{{VISIBILITY}}"
