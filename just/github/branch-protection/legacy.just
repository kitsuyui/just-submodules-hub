github_branch_protection_legacy_source_dir := source_directory()

# Show legacy default-branch rulesets and whether they can be deleted safely.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_legacy_source_dir}}/../../../scripts/github/default-branch-ruleset.sh" legacy-status "{{REPO}}"
