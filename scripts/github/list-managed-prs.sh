#!/bin/sh
set -eu

state="${1:-open}"

case "$state" in
  open)
    state_mode="open"
    ;;
  closed)
    state_mode="closed"
    ;;
  merged)
    state_mode="merged"
    ;;
  all)
    state_mode="all"
    ;;
  *)
    echo "STATE must be one of: open, closed, merged, all" >&2
    exit 2
    ;;
esac

command -v gh >/dev/null 2>&1 || {
  echo "gh command not found" >&2
  exit 1
}

if ! gh auth status >/dev/null 2>&1; then
  echo "gh authentication is invalid. Run: gh auth login -h github.com" >&2
  exit 1
fi

managed_file=$(mktemp)
all_file=$(mktemp)
trap 'rm -f "$managed_file" "$all_file"' EXIT

git config -f .gitmodules --get-regexp '^submodule\..*\.path$' \
  | awk '{print $2}' \
  | sed 's#^repo/github.com/##' \
  | sort -u > "$managed_file"

owners=$(cut -d'/' -f1 "$managed_file" | sort -u)

printf 'repo\tauthor\turl\n' > "$all_file"

for owner in $owners; do
  if [ "$state_mode" = "open" ]; then
    gh search prs --owner "$owner" --state open --limit 1000 \
      --json number,title,author,updatedAt,url,isDraft,state,repository \
      --jq '.[] | [.repository.nameWithOwner, .author.login, .url] | @tsv' \
      >> "$all_file"
  elif [ "$state_mode" = "closed" ]; then
    gh search prs --owner "$owner" --state closed --limit 1000 \
      --json number,title,author,updatedAt,url,isDraft,state,repository \
      --jq '.[] | [.repository.nameWithOwner, .author.login, .url] | @tsv' \
      >> "$all_file"
  elif [ "$state_mode" = "merged" ]; then
    gh search prs --owner "$owner" --merged --limit 1000 \
      --json number,title,author,updatedAt,url,isDraft,state,repository \
      --jq '.[] | [.repository.nameWithOwner, .author.login, .url] | @tsv' \
      >> "$all_file"
  else
    gh search prs --owner "$owner" --limit 1000 \
      --json number,title,author,updatedAt,url,isDraft,state,repository \
      --jq '.[] | [.repository.nameWithOwner, .author.login, .url] | @tsv' \
      >> "$all_file"
  fi
done

awk 'BEGIN{FS=OFS="\t"} NR==FNR {managed[$1]=1; next} FNR==1 {print; next} ($1 in managed) {print}' \
  "$managed_file" "$all_file"
