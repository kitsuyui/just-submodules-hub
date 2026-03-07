#!/bin/sh
set -eu

# Detect duplicated basenames among git-tracked files in recursive submodules.
# Output format:
#   <filename> (<count>)
#     - <submodule/path/to/file>

if [ "$#" -ne 0 ]; then
  echo "usage: $0" >&2
  exit 2
fi

# shellcheck disable=SC2016
git submodule foreach --recursive --quiet '
  git ls-files | sed "s#^#$sm_path/#"
' \
| awk '
  {
    path = $0
    base = $0
    sub(".*/", "", base)
    lower = tolower(base)

    # Exclude common source files that are expected to overlap across projects.
    if (lower ~ /\.(c|cc|cpp|cxx|h|hh|hpp|hxx|cs|go|java|js|jsx|kt|kts|lua|m|mm|php|pl|py|rb|rs|scala|sh|swift|ts|tsx|zsh|snap|svg|mdx|ambr|mjs|lock)$/ || lower == "py.typed") {
      next
    }

    print base "|" path
  }
' \
| sort \
| awk -F'\\|' '
  function flush() {
    if (count > 1) {
      print current " (" count ")"
      printf "%s", paths
      print ""
    }
  }
  NR == 1 {
    current = $1
    count = 0
    paths = ""
  }
  $1 != current {
    flush()
    current = $1
    count = 0
    paths = ""
  }
  {
    count++
    paths = paths "\n  - " $2
  }
  END {
    flush()
  }
'
