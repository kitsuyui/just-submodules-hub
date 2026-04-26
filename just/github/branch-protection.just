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

# Deprecated alias for legacy::status.
legacy-status REPO:
  #!/bin/sh
  echo "warning: github::branch-protection::legacy-status is deprecated; use github::branch-protection::legacy::status" >&2
  cd "{{invocation_directory()}}" && just github branch-protection legacy status "{{REPO}}"

# Deprecated alias for ruleset::cleanup.
cleanup-ruleset REPO IDENTIFIER:
  #!/bin/sh
  echo "warning: github::branch-protection::cleanup-ruleset is deprecated; use github::branch-protection::ruleset::cleanup" >&2
  cd "{{invocation_directory()}}" && just github branch-protection ruleset cleanup "{{REPO}}" "{{IDENTIFIER}}"

# Deprecated alias for classic::status.
classic-status REPO:
  #!/bin/sh
  echo "warning: github::branch-protection::classic-status is deprecated; use github::branch-protection::classic::status" >&2
  cd "{{invocation_directory()}}" && just github branch-protection classic status "{{REPO}}"

# Deprecated alias for classic::cleanup.
cleanup-classic REPO:
  #!/bin/sh
  echo "warning: github::branch-protection::cleanup-classic is deprecated; use github::branch-protection::classic::cleanup" >&2
  cd "{{invocation_directory()}}" && just github branch-protection classic cleanup "{{REPO}}"

# Deprecated alias for all::status.
status-all VISIBILITY="public":
  #!/bin/sh
  echo "warning: github::branch-protection::status-all is deprecated; use github::branch-protection::all::status" >&2
  cd "{{invocation_directory()}}" && just github branch-protection all status "{{VISIBILITY}}"

# Deprecated alias for all::apply.
apply-all VISIBILITY="public":
  #!/bin/sh
  echo "warning: github::branch-protection::apply-all is deprecated; use github::branch-protection::all::apply" >&2
  cd "{{invocation_directory()}}" && just github branch-protection all apply "{{VISIBILITY}}"

# Deprecated alias for all::rulesets::cleanup.
cleanup-rulesets-all VISIBILITY="public":
  #!/bin/sh
  echo "warning: github::branch-protection::cleanup-rulesets-all is deprecated; use github::branch-protection::all::rulesets::cleanup" >&2
  cd "{{invocation_directory()}}" && just github branch-protection all rulesets cleanup "{{VISIBILITY}}"

# Deprecated alias for all::classic::cleanup.
cleanup-classic-all VISIBILITY="public":
  #!/bin/sh
  echo "warning: github::branch-protection::cleanup-classic-all is deprecated; use github::branch-protection::all::classic::cleanup" >&2
  cd "{{invocation_directory()}}" && just github branch-protection all classic cleanup "{{VISIBILITY}}"
