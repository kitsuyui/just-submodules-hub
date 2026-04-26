github_branch_protection_all_classic_source_dir := source_directory()

# Delete redundant classic branch protection for all managed repositories and skip manual-review cases.
cleanup VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_all_classic_source_dir}}/../../../../scripts/github/default-branch-baseline-bulk.sh" cleanup-classic-all "{{VISIBILITY}}"
