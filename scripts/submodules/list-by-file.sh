#!/bin/sh
set -eu

if [ "$#" -ne 1 ]; then
  echo "usage: $0 <marker-file>" >&2
  exit 2
fi

marker_file="$1"

git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | while read -r _ path; do
  if find "$path" -name "$marker_file" -print -quit | grep -q .; then
    echo "$path"
  fi
done
