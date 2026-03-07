#!/bin/sh
set -eu

action="${1:-}"
if [ -z "$action" ]; then
  echo "action is required" >&2
  exit 2
fi
shift

summary="$(just --summary)"
has_recipe() {
  printf '%s\n' "$summary" | tr ' ' '\n' | grep -qx "$1"
}

before_hook="before-${action}"
after_hook="after-${action}"

if has_recipe "$before_hook"; then
  just "$before_hook" "$@"
fi

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
"$script_dir/run-action.sh" "$action" "$@"
if has_recipe "$after_hook"; then
  just "$after_hook" "$@"
fi
