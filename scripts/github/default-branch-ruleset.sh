#!/bin/sh
set -eu

command -v gh >/dev/null 2>&1 || {
  echo "gh command not found" >&2
  exit 1
}

gh auth status >/dev/null 2>&1 || {
  echo "gh auth login is required" >&2
  exit 1
}

script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH='' cd -- "$script_dir/../.." && pwd)

PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" \
  exec uv run --project "$project_root" python "$script_dir/default_branch_ruleset.py" "$@"
