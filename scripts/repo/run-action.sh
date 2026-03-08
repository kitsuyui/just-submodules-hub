#!/bin/sh
set -eu

action="${1:-}"
if [ -z "$action" ]; then
  echo "action is required" >&2
  exit 2
fi
shift
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
sync_script="$script_dir/sync-default-branch.sh"
open_repo_script="$script_dir/open-repo.sh"

repo_input_to_path() {
  input="$1"
  if [ -z "$input" ]; then
    echo "REPO is required" >&2
    exit 2
  fi

  case "$input" in
    repo/github.com/*)
      printf '%s\n' "$input"
      return 0
      ;;
  esac

  repo_path=$(echo "$input" | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##')
  printf 'repo/github.com/%s\n' "$repo_path"
}

case "$action" in
  add-repo)
    repo_url_input="${1:-}"
    if [ -z "$repo_url_input" ]; then
      echo "REPO_URL is required" >&2
      exit 2
    fi
    repo_path=$(echo "$repo_url_input" | sed -E 's#^(git@github.com:|https://github.com/)##; s#\.git$##')
    repo_url="git@github.com:${repo_path}.git"
    repo_dir="repo/github.com/${repo_path}"
    # Clean up leftovers from a previously failed add (only under .git/modules)
    if [ -d ".git/modules/${repo_dir}" ] && [ ! -d "${repo_dir}" ]; then
      rm -rf ".git/modules/${repo_dir}"
    fi
    git submodule add -- "${repo_url}" "${repo_dir}"
    ;;

  remove-repo)
    repo_input="${1:-}"
    repo_path=$(repo_input_to_path "$repo_input")
    git submodule deinit -f -- "$repo_path"
    rm -rf ".git/modules/$repo_path"
    git rm -f "$repo_path"
    ;;

  create-public-repo)
    repo="${1:-}"
    if [ -z "$repo" ]; then
      echo "REPO is required" >&2
      exit 2
    fi
    command -v gh >/dev/null 2>&1 || { echo "gh command not found" >&2; exit 1; }
    if gh repo view "$repo" >/dev/null 2>&1; then
      echo "Repository $repo already exists. Skipping creation."
    else
      gh repo create "$repo" --public --add-readme
    fi
    just add-repo "https://github.com/$repo"
    ;;

  create-private-repo)
    repo="${1:-}"
    if [ -z "$repo" ]; then
      echo "REPO is required" >&2
      exit 2
    fi
    command -v gh >/dev/null 2>&1 || { echo "gh command not found" >&2; exit 1; }
    if gh repo view "$repo" >/dev/null 2>&1; then
      echo "Repository $repo already exists. Skipping creation."
    else
      gh repo create "$repo" --private --add-readme
    fi
    just add-repo "https://github.com/$repo"
    ;;

  sync-repo-default-branch)
    repo_input="${1:-}"
    repo_path=$(repo_input_to_path "$repo_input")
    shift
    "$sync_script" one "$repo_path" "$@"
    ;;

  sync-all-repo-default-branch)
    final_submodule_update=0
    if [ "${1:-}" = "--final-submodule-update" ]; then
      final_submodule_update=1
      shift
    fi

    "$sync_script" all "$@"
    if [ "$final_submodule_update" -eq 1 ]; then
      echo "Running final submodule update (--remote --rebase --recursive)..."
      git submodule update --remote --rebase --recursive --progress
    fi
    ;;

  commit-submodule-pointers)
    message="${1:-Update submodule pointers}"
    changed=""
    while IFS= read -r repo_path; do
      [ -n "$repo_path" ] || continue
      if ! git diff --quiet -- "$repo_path"; then
        changed="$changed $repo_path"
      fi
    done <<EOF_PATHS
$(git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}')
EOF_PATHS

    if [ -z "$changed" ]; then
      echo "No submodule pointer changes to commit"
      exit 0
    fi

    # shellcheck disable=SC2086
    git add -- $changed
    if git diff --cached --quiet; then
      echo "No staged changes after selecting submodule pointers"
      exit 0
    fi
    git commit -m "$message"
    ;;

  open-repo)
    tool="${1:-}"
    repo_input="${2:-}"
    if [ -z "$tool" ] || [ -z "$repo_input" ]; then
      echo "TOOL and REPO are required" >&2
      exit 2
    fi
    exec "$open_repo_script" "$tool" "$repo_input"
    ;;

  every-repo)
    command_to_run="${1:-}"
    if [ -z "$command_to_run" ]; then
      echo "COMMAND is required" >&2
      exit 2
    fi
    # Iterate over submodule paths and run the command
    git submodule foreach --recursive "echo \"Running command in \$path\"; $command_to_run"
    ;;

  grep)
    git grep --recurse-submodules "$@"
    ;;

  list-github-repos-owner)
    owner="${1:-}"
    visibility="${2:-}"
    if [ -z "$owner" ] || [ -z "$visibility" ]; then
      echo "OWNER and VISIBILITY are required" >&2
      exit 2
    fi
    command -v gh >/dev/null 2>&1 || { echo "gh command not found" >&2; exit 1; }
    case "$visibility" in
      public|private|internal|all) ;;
      *)
        echo "VISIBILITY must be one of: public/private/internal/all: $visibility" >&2
        exit 2
        ;;
    esac
    if [ "$visibility" = "all" ]; then
      gh repo list "$owner" --limit 1000 --json nameWithOwner,url,isArchived,isFork --jq '.[] | select((.isArchived | not) and (.isFork | not)) | "\(.nameWithOwner)\t\(.url)"'
    else
      gh repo list "$owner" --visibility "$visibility" --limit 1000 --json nameWithOwner,url,isArchived,isFork --jq '.[] | select((.isArchived | not) and (.isFork | not)) | "\(.nameWithOwner)\t\(.url)"'
    fi
    ;;

  list-github-repos)
    owners="${1:-}"
    visibility="${2:-}"
    if [ -z "$owners" ] || [ -z "$visibility" ]; then
      echo "OWNERS and VISIBILITY are required" >&2
      exit 2
    fi
    command -v gh >/dev/null 2>&1 || { echo "gh command not found" >&2; exit 1; }
    for owner in $(printf '%s\n' "$owners" | tr ',' ' '); do
      [ -n "$owner" ] || continue
      just list-github-repos-owner "$owner" "$visibility"
    done | awk -F'\t' '!seen[$1]++'
    ;;

  list-managed-repos)
    git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' | sed 's#^repo/github.com/##' | sort
    ;;

  list-unmanaged-repos)
    owners="${1:-}"
    visibility="${2:-}"
    if [ -z "$owners" ] || [ -z "$visibility" ]; then
      echo "OWNERS and VISIBILITY are required" >&2
      exit 2
    fi
    public_file=$(mktemp)
    managed_file=$(mktemp)
    trap 'rm -f "$public_file" "$managed_file"' EXIT
    just list-github-repos "$owners" "$visibility" | cut -f1 | sort > "$public_file"
    just list-managed-repos | sort > "$managed_file"
    comm -23 "$public_file" "$managed_file"
    ;;

  *)
    echo "Unknown action: $action" >&2
    exit 2
    ;;
esac
