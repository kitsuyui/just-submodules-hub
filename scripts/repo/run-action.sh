#!/bin/sh
set -eu

action="${1:-}"
if [ -z "$action" ]; then
  echo "action is required" >&2
  exit 2
fi
shift
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
project_root=$(CDPATH='' cd -- "$script_dir/../.." && pwd)
sync_script="$script_dir/sync-default-branch.sh"
open_repo_script="$script_dir/open-repo.sh"
resolve_repo_script="$script_dir/resolve_repo.py"
reconcile_worktrees_script="$script_dir/reconcile_submodule_worktrees.py"
submodule_command_script="$script_dir/run_submodule_command.py"
cleanup_branches_script="$script_dir/cleanup_merged_branches.py"
linked_worktrees_script="$script_dir/list_linked_worktrees.py"

repo_input_to_path() {
  input="$1"
  if [ -z "$input" ]; then
    echo "REPO is required" >&2
    exit 2
  fi
  uv run --project "$project_root" python "$resolve_repo_script" "$input"
}

submodule_section_names() {
  git config -f .gitmodules --name-only --get-regexp '^submodule\..*\.path$' 2>/dev/null | sed 's/\.path$//'
}

submodule_path_from_section() {
  section="$1"
  git config -f .gitmodules --get "${section}.path"
}

target_submodule_sections() {
  repo_input="${1:-}"

  if [ -z "$repo_input" ]; then
    submodule_section_names
    return
  fi

  repo_path=$(repo_input_to_path "$repo_input")
  section_name=$(git config -f .gitmodules --name-only --get-regexp '^submodule\..*\.path$' 2>/dev/null \
    | while IFS= read -r candidate; do
        [ -n "$candidate" ] || continue
        section=${candidate%.path}
        path=$(git config -f .gitmodules --get "${section}.path")
        if [ "$path" = "$repo_path" ]; then
          printf '%s\n' "$section"
          break
        fi
      done)

  if [ -z "$section_name" ]; then
    echo "Managed submodule not found: $repo_input" >&2
    exit 2
  fi

  printf '%s\n' "$section_name"
}

set_submodule_ignore_value() {
  ignore_value="$1"
  repo_input="${2:-}"

  target_submodule_sections "$repo_input" | while IFS= read -r section; do
    [ -n "$section" ] || continue
    git config --local "${section}.ignore" "$ignore_value"
  done
}

clear_submodule_ignore_value() {
  repo_input="${1:-}"

  target_submodule_sections "$repo_input" | while IFS= read -r section; do
    [ -n "$section" ] || continue
    git config --local --unset-all "${section}.ignore" 2>/dev/null || true
  done
}

print_submodule_ignore_raw_status() {
  expected_value="$1"
  repo_input="${2:-}"

  target_submodule_sections "$repo_input" | while IFS= read -r section; do
    [ -n "$section" ] || continue
    repo_path=$(submodule_path_from_section "$section")
    ignore_value=$(git config --local --get "${section}.ignore" 2>/dev/null || true)
    if [ "$ignore_value" = "$expected_value" ]; then
      printf '%s\t%s\n' "$repo_path" "$ignore_value"
    else
      printf '%s\toff\n' "$repo_path"
    fi
  done
}

print_submodule_visibility_status() {
  expected_value="$1"
  repo_input="${2:-}"

  target_submodule_sections "$repo_input" | while IFS= read -r section; do
    [ -n "$section" ] || continue
    repo_path=$(submodule_path_from_section "$section")
    ignore_value=$(git config --local --get "${section}.ignore" 2>/dev/null || true)
    if [ "$ignore_value" = "$expected_value" ]; then
      printf '%s\thidden\n' "$repo_path"
    else
      printf '%s\tvisible\n' "$repo_path"
    fi
  done
}

warn_deprecated_submodule_action() {
  old_name="$1"
  new_name="$2"
  printf 'warning: %s is deprecated; use %s instead\n' "$old_name" "$new_name" >&2
}

submodule_pointer_changed() {
  repo_path="$1"
  index_oid=$(git ls-files -s -- "$repo_path" | awk '{print $2}')
  if [ -z "$index_oid" ]; then
    return 1
  fi

  worktree_oid=$(git -C "$repo_path" rev-parse HEAD 2>/dev/null || true)
  if [ -z "$worktree_oid" ]; then
    return 1
  fi

  [ "$index_oid" != "$worktree_oid" ]
}

resolve_submodule_jobs() {
  requested_jobs="${1:-}"
  if [ -n "$requested_jobs" ]; then
    printf '%s\n' "$requested_jobs"
    return
  fi

  configured_jobs=$(git config --get submodule.fetchJobs 2>/dev/null || true)
  if [ -n "$configured_jobs" ]; then
    printf '%s\n' "$configured_jobs"
    return
  fi

  if command -v getconf >/dev/null 2>&1; then
    cpu_count=$(getconf _NPROCESSORS_ONLN 2>/dev/null || true)
    if [ -n "$cpu_count" ]; then
      printf '%s\n' "$cpu_count"
      return
    fi
  fi

  if command -v sysctl >/dev/null 2>&1; then
    cpu_count=$(sysctl -n hw.ncpu 2>/dev/null || true)
    if [ -n "$cpu_count" ]; then
      printf '%s\n' "$cpu_count"
    fi
  fi
}

validate_positive_integer() {
  value="$1"
  label="$2"
  case "$value" in
    ''|*[!0-9]*|0)
      echo "$label must be a positive integer: $value" >&2
      exit 2
      ;;
  esac
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
    git config -f .gitmodules "submodule.${repo_dir}.shallow" true
    git config --local "submodule.${repo_dir}.ignore" all
    ;;

  init-all-repos)
    jobs=$(resolve_submodule_jobs "${1:-}")
    if [ -n "$jobs" ]; then
      validate_positive_integer "$jobs" "JOBS"
      git -c protocol.file.allow=always submodule update --init --recursive --recommend-shallow --jobs "$jobs"
    else
      git -c protocol.file.allow=always submodule update --init --recursive --recommend-shallow
    fi
    set_submodule_ignore_value all
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
    just repo submodule add "https://github.com/$repo"
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
    just repo submodule add "https://github.com/$repo"
    ;;

  sync-repo-default-branch)
    repo_input="${1:-}"
    shift
    "$sync_script" one "$repo_input" "$@"
    ;;

  sync-all-repo-default-branch)
    final_submodule_update=0
    if [ "${1:-}" = "--final-submodule-update" ]; then
      final_submodule_update=1
      shift
    fi

    "$sync_script" all "$@"
    if [ "$final_submodule_update" -eq 1 ]; then
      echo "Running final submodule update (--remote --rebase --recursive --recommend-shallow)..."
      git submodule update --remote --rebase --recursive --recommend-shallow --progress
    fi
    ;;

  reconcile-submodule-worktree)
    repo_input="${1:-}"
    shift
    if [ -z "$repo_input" ]; then
      echo "REPO is required" >&2
      exit 2
    fi
    uv run --project "$project_root" python "$reconcile_worktrees_script" one "$repo_input" "$@"
    ;;

  reconcile-submodule-worktrees)
    uv run --project "$project_root" python "$reconcile_worktrees_script" all "$@"
    ;;

  reconcile-worktrees)
    uv run --project "$project_root" python "$reconcile_worktrees_script" root-and-all "$@"
    ;;

  cleanup-branches)
    uv run --project "$project_root" python "$cleanup_branches_script" one "$@"
    ;;

  cleanup-submodule-branches)
    uv run --project "$project_root" python "$cleanup_branches_script" all "$@"
    ;;

  cleanup-worktree-branches)
    uv run --project "$project_root" python "$cleanup_branches_script" root-and-all "$@"
    ;;

  list-linked-worktrees)
    uv run --project "$project_root" python "$linked_worktrees_script" "$@"
    ;;

  commit-submodule-pointers)
    message="${1:-Update submodule pointers}"
    changed=""
    while IFS= read -r repo_path; do
      [ -n "$repo_path" ] || continue
      if submodule_pointer_changed "$repo_path"; then
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
    if git diff --cached --ignore-submodules=none --quiet; then
      echo "No staged changes after selecting submodule pointers"
      exit 0
    fi
    git commit -m "$message"
    ;;

  submodule-root-status-hide)
    repo_input="${1:-}"
    set_submodule_ignore_value all "$repo_input"
    ;;

  submodule-root-status-show)
    repo_input="${1:-}"
    clear_submodule_ignore_value "$repo_input"
    ;;

  submodule-root-status-visibility)
    repo_input="${1:-}"
    print_submodule_visibility_status all "$repo_input"
    ;;

  submodule-hide-root-status-changes|submodule-hide-worktree-changes|submodule-hide-all-changes|submodule-ignore-all-on)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-hide"
    set_submodule_ignore_value all "$repo_input"
    ;;

  submodule-show-root-status-changes|submodule-show-worktree-changes|submodule-show-all-changes|submodule-ignore-all-off)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-show"
    clear_submodule_ignore_value "$repo_input"
    ;;

  submodule-root-status-changes-visibility|submodule-worktree-changes-visibility|submodule-all-changes-visibility)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-visibility"
    print_submodule_visibility_status all "$repo_input"
    ;;

  submodule-ignore-dirty-status)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-visibility"
    print_submodule_ignore_raw_status dirty "$repo_input"
    ;;

  submodule-ignore-dirty-on)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-hide"
    set_submodule_ignore_value dirty "$repo_input"
    ;;

  submodule-ignore-dirty-off)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-show"
    clear_submodule_ignore_value "$repo_input"
    ;;

  submodule-ignore-all-status)
    repo_input="${1:-}"
    warn_deprecated_submodule_action "$action" "submodule-root-status-visibility"
    print_submodule_ignore_raw_status all "$repo_input"
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
    if [ "$#" -eq 0 ]; then
      echo "COMMAND is required" >&2
      exit 2
    fi
    uv run --project "$project_root" python "$submodule_command_script" "$@"
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
      just github repos owner list "$owner" "$visibility"
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
    just github repos list "$owners" "$visibility" | cut -f1 | sort > "$public_file"
    just repo submodule managed list | sort > "$managed_file"
    comm -23 "$public_file" "$managed_file"
    ;;

  *)
    echo "Unknown action: $action" >&2
    exit 2
    ;;
esac
