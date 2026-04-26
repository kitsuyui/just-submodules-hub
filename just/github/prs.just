github_prs_source_dir := source_directory()

mod summaries "prs/summaries.just"

# List pull requests for managed submodules (STATE: open/closed/merged/all).
list STATE="open":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-managed-prs.sh" "{{STATE}}"

# Deprecated compatibility alias. Prefer summaries::show.
alias summary := summaries::show
