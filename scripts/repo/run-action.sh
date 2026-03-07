#!/bin/sh
set -eu

action="${1:-}"
if [ -z "$action" ]; then
  echo "action is required" >&2
  exit 2
fi
shift

sync_verbose_raw="${SYNC_VERBOSE:-0}"
sync_jobs_raw="${SYNC_JOBS:-4}"

case "$sync_verbose_raw" in
  1|true|TRUE|yes|YES|on|ON) sync_verbose=1 ;;
  *) sync_verbose=0 ;;
esac

case "$sync_jobs_raw" in
  ''|*[!0-9]*) sync_jobs=4 ;;
  *) sync_jobs="$sync_jobs_raw" ;;
esac

if [ "$sync_jobs" -lt 1 ]; then
  sync_jobs=1
fi

run_quiet_stdout() {
  cmd_output_file=$(mktemp)
  if "$@" >"$cmd_output_file" 2>&1; then
    rm -f "$cmd_output_file"
    return 0
  fi

  cat "$cmd_output_file" >&2
  rm -f "$cmd_output_file"
  return 1
}

repo_display_name() {
  repo_path="$1"
  printf '%s\n' "${repo_path#repo/github.com/}"
}

format_sync_result() {
  repo_path="$1"
  default_branch="$2"
  switched="$3"
  updated="$4"

  if [ "$switched" -eq 0 ] && [ "$updated" -eq 0 ]; then
    printf 'OK\t%s\t%s\tnochange\n' "$repo_path" "$default_branch"
    return 0
  fi

  printf 'OK\t%s\t%s\tchanged\tswitched=%s\tupdated=%s\n' "$repo_path" "$default_branch" "$switched" "$updated"
}

print_sync_result() {
  result_line="$1"

  IFS="$(printf '\t')" read -r status repo_path default_branch state switched_field updated_field <<EOF_RESULT
$result_line
EOF_RESULT

  repo_name=$(repo_display_name "$repo_path")
  case "$state" in
    nochange)
      if [ "$sync_verbose" -eq 1 ]; then
        echo "${repo_name}: up-to-date"
      fi
      ;;
    changed)
      switched="${switched_field#switched=}"
      updated="${updated_field#updated=}"
      message="${repo_name}:"
      if [ "$switched" = "1" ]; then
        message="${message} switched-to:${default_branch}"
      fi
      if [ "$updated" = "1" ]; then
        message="${message} updated-to:latest"
      fi
      echo "$message"
      ;;
  esac
}

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

sync_repo_path_to_default_branch() {
  repo_path="$1"
  # Submodules have a ".git" file, while regular repos have a ".git" directory.
  if [ ! -e "$repo_path/.git" ]; then
    echo "Repository path not found: $repo_path" >&2
    exit 2
  fi

  (
    cd "$repo_path"
    current_branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "DETACHED")
    switched=0
    updated=0

    run_quiet_stdout git fetch origin --prune

    default_branch=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)
    if [ -z "$default_branch" ]; then
      default_branch=$(git remote show origin | sed -n 's#.*HEAD branch: ##p' | head -n1)
    fi

    if [ -z "$default_branch" ]; then
      echo "Could not resolve default branch for $repo_path" >&2
      exit 2
    fi

    if [ "$current_branch" != "$default_branch" ]; then
      switched=1
    fi

    run_quiet_stdout git switch "$default_branch"
    before_pull=$(git rev-parse HEAD)
    run_quiet_stdout git pull --ff-only origin "$default_branch"
    after_pull=$(git rev-parse HEAD)

    if [ "$before_pull" != "$after_pull" ]; then
      updated=1
    fi

    format_sync_result "$repo_path" "$default_branch" "$switched" "$updated"
  )
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
    sync_result=$(sync_repo_path_to_default_branch "$repo_path")
    print_sync_result "$sync_result"
    ;;

  sync-repo-default-branch-machine)
    repo_input="${1:-}"
    repo_path=$(repo_input_to_path "$repo_input")
    sync_repo_path_to_default_branch "$repo_path"
    ;;

  sync-all-repo-default-branch)
    paths_file=$(mktemp)
    results_file=$(mktemp)
    trap 'rm -f "$paths_file" "$results_file"' EXIT

    git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' >"$paths_file"
    if [ ! -s "$paths_file" ]; then
      echo "No submodule paths found in .gitmodules"
      exit 0
    fi

    sync_failed=0
    if [ "$sync_jobs" -le 1 ]; then
      while IFS= read -r repo_path; do
        [ -n "$repo_path" ] || continue
        if ! "$0" sync-repo-default-branch-machine "$repo_path" >>"$results_file"; then
          sync_failed=1
        fi
      done <"$paths_file"
    else
      if ! xargs -P "$sync_jobs" -I{} sh -c '"$1" sync-repo-default-branch-machine "$2"' _ "$0" "{}" <"$paths_file" >>"$results_file"; then
        sync_failed=1
      fi
    fi

    while IFS= read -r result_line; do
      [ -n "$result_line" ] || continue
      print_sync_result "$result_line"
    done <"$results_file"

    if [ "$sync_failed" -ne 0 ]; then
      echo "One or more repositories failed to sync" >&2
      exit 1
    fi

    git submodule update --remote --rebase --recursive --progress
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
