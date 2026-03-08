github_prs_source_dir := source_directory()

# List pull requests for managed submodules (STATE: open/closed/merged/all).
list STATE="open":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-managed-prs.sh" "{{STATE}}"

# Show a per-repository summary of managed pull requests (STATE: open/closed/merged/all).
summary STATE="open":
  #!/bin/sh
  set -eu
  tmp_file=$(mktemp)
  trap 'rm -f "$tmp_file"' EXIT
  cd "{{invocation_directory()}}" && "{{github_prs_source_dir}}/../../scripts/github/list-managed-prs.sh" "{{STATE}}" > "$tmp_file"
  awk 'BEGIN{FS=OFS="\t"} FNR==1{next} {count[$1]++} END{print "repo","prs"; for (r in count) print r,count[r]}' "$tmp_file" | sort
