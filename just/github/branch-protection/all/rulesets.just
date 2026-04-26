github_branch_protection_all_rulesets_source_dir := source_directory()

# Delete redundant legacy rulesets for all managed repositories and skip manual-review cases.
cleanup VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_all_rulesets_source_dir}}/../../../../scripts/github/default-branch-baseline-bulk.sh" cleanup-rulesets-all "{{VISIBILITY}}"
