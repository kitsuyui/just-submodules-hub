github_prs_summaries_source_dir := source_directory()

# Show a per-repository summary of managed pull requests (STATE: open/closed/merged/all).
show STATE="open":
  #!/bin/sh
  set -eu
  tmp_file=$(mktemp)
  trap 'rm -f "$tmp_file"' EXIT
  cd "{{invocation_directory()}}" && "{{github_prs_summaries_source_dir}}/../../../scripts/github/list-managed-prs.sh" "{{STATE}}" > "$tmp_file"
  awk 'BEGIN{FS=OFS="\t"} FNR==1{next} {count[$1]++} END{print "repo","prs"; for (r in count) print r,count[r]}' "$tmp_file" | sort
