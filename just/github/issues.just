github_issues_source_dir := source_directory()

mod summaries "issues/summaries.just"

# List issues for managed submodules (STATE: open/closed/all).
list STATE="open":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_issues_source_dir}}/../../scripts/github/list-managed-issues.sh" "{{STATE}}"

# Deprecated compatibility alias. Prefer summaries::show.
alias summary := summaries::show
