github_prs_source_dir := source_directory()

mod summaries "prs/summaries.just"

# List pull requests for managed submodules (STATE: open/closed/merged/all).
list STATE="open":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-managed-prs.sh" "{{STATE}}"

# List open pull requests that can be merged as-is (mergeable, checks green).
ready:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-ready-prs.sh"

# List open pull requests that cannot become ready without an external action.
action-required:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-action-required-prs.sh"

# List action-required pull requests that generic automation must leave to an operator.
operator-required:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-operator-required-prs.sh"

# Deprecated compatibility alias. Prefer summaries::show.
alias summary := summaries::show
