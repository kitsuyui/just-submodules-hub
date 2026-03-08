# List pull requests for managed submodules (STATE: open/closed/merged/all).
list-managed-prs STATE="open":
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/list-managed-prs.sh" "{{STATE}}"

# Show baseline ruleset status for one repository default branch.
default-branch-ruleset-status REPO:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" status "{{REPO}}"

# Create or update the managed baseline ruleset for one repository default branch.
default-branch-ruleset-apply REPO:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" apply "{{REPO}}"

# Show legacy default-branch rulesets and whether they can be deleted safely.
default-branch-ruleset-legacy-status REPO:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" legacy-status "{{REPO}}"

# Delete one legacy default-branch ruleset only when remaining active rulesets already cover it.
default-branch-ruleset-delete-if-redundant REPO IDENTIFIER:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" delete-if-redundant "{{REPO}}" "{{IDENTIFIER}}"

# Show classic branch protection status for the default branch and whether it is redundant.
default-branch-classic-protection-status REPO:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" classic-status "{{REPO}}"

# Delete classic branch protection only when remaining effective rules already cover it.
default-branch-classic-protection-delete-if-redundant REPO:
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-ruleset.sh" classic-delete-if-redundant "{{REPO}}"

# Show ruleset/classic protection status for all managed repositories (VISIBILITY: public/private/all).
default-branch-baseline-status-all VISIBILITY="public":
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-baseline-bulk.sh" status-all "{{VISIBILITY}}"

# Create or update the managed baseline ruleset for all managed repositories.
default-branch-baseline-apply-all VISIBILITY="public":
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-baseline-bulk.sh" apply-all "{{VISIBILITY}}"

# Delete redundant legacy rulesets for all managed repositories and skip manual-review cases.
default-branch-baseline-cleanup-rulesets-all VISIBILITY="public":
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-baseline-bulk.sh" cleanup-rulesets-all "{{VISIBILITY}}"

# Delete redundant classic branch protection for all managed repositories and skip manual-review cases.
default-branch-baseline-cleanup-classic-all VISIBILITY="public":
  #!/bin/sh
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/default-branch-baseline-bulk.sh" cleanup-classic-all "{{VISIBILITY}}"

# Show a per-repository summary of managed pull requests (STATE: open/closed/merged/all).
list-managed-prs-summary STATE="open":
  #!/bin/sh
  set -eu
  tmp_file=$(mktemp)
  trap 'rm -f "$tmp_file"' EXIT
  "repo/github.com/kitsuyui/just-submodules-hub/scripts/github/list-managed-prs.sh" "{{STATE}}" > "$tmp_file"
  awk 'BEGIN{FS=OFS="\t"} FNR==1{next} {count[$1]++} END{print "repo","prs"; for (r in count) print r,count[r]}' "$tmp_file" | sort
