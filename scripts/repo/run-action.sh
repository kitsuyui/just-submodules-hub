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
resolve_repo_script="$script_dir/resolve_repo.py"
linked_worktrees_script="$script_dir/list_linked_worktrees.py"
linked_worktree_sync_plan_script="$script_dir/plan_linked_worktree_sync.py"
linked_worktree_sync_apply_script="$script_dir/apply_linked_worktree_sync.py"
linked_worktree_safety_script="$script_dir/linked_worktree_safety.py"

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

print_managed_repos() {
  git config -f .gitmodules --get-regexp '^submodule\..*\.path$' 2>/dev/null | awk '{print $2}' | sed 's#^repo/github.com/##' | sort
}

filter_repos_by_owners() {
  owners="$1"
  awk -v owners="$owners" '
    BEGIN {
      n = split(owners, owner_list, /[ ,]+/)
      for (i = 1; i <= n; i++) {
        if (owner_list[i] != "") {
          allowed[owner_list[i]] = 1
        }
      }
    }
    {
      split($0, parts, "/")
      if (allowed[parts[1]]) {
        print
      }
    }
  '
}

validate_github_repo_visibility() {
  visibility="$1"
  case "$visibility" in
    public|private|internal|all) ;;
    *)
      echo "VISIBILITY must be one of: public/private/internal/all: $visibility" >&2
      exit 2
      ;;
  esac
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

run_init_all_in_worktree() {
  worktree_path="$1"
  init_mode="$2"
  init_jobs="$3"

  if [ -n "$init_jobs" ]; then
    validate_positive_integer "$init_jobs" "JOBS"
  fi

  set -- init-all-repos --force
  case "$init_mode" in
    fetch-fallback)
      set -- "$@" --fetch-fallback
      ;;
    no-fetch)
      set -- "$@" --no-fetch
      ;;
    normal)
      ;;
    *)
      echo "unknown submodule init mode: $init_mode" >&2
      exit 2
      ;;
  esac

  if [ -n "$init_jobs" ]; then
    set -- "$@" --jobs "$init_jobs"
  fi

  (cd "$worktree_path" && "$script_dir/run-action.sh" "$@")
}



# Actions migrated to the Python entrypoint (#60 item 3, phases 1-2).
case "$action" in
  list-github-repos-owner|list-github-repos|list-managed-repos|list-unmanaged-repos|open-repo|every-repo|grep|\
init-all-repos|sync-repo-default-branch|sync-all-repo-default-branch|reconcile-submodule-worktree|reconcile-submodule-worktrees|reconcile-worktrees|cleanup-branches|cleanup-submodule-branches|cleanup-worktree-branches)
    exec uv run --project "$project_root" env PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" python -m just_submodules_hub.run_action "$action" "$@"
    ;;
esac

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




  list-linked-worktrees)
    uv run --project "$project_root" python "$linked_worktrees_script" "$@"
    ;;

  plan-linked-worktree-sync)
    uv run --project "$project_root" python "$linked_worktree_sync_plan_script" "$@"
    ;;

  apply-linked-worktree-sync)
    uv run --project "$project_root" python "$linked_worktree_sync_apply_script" "$@"
    ;;

  install-linked-worktree-hooks)
    uv run --project "$project_root" python "$linked_worktree_safety_script" install-hooks "$@"
    ;;

  reset-linked-worktree)
    uv run --project "$project_root" python "$linked_worktree_safety_script" reset "$@"
    ;;

  cleanup-linked-worktrees)
    uv run --project "$project_root" python "$linked_worktree_safety_script" cleanup "$@"
    ;;

  add-linked-worktree)
    worktree_path="${1:-}"
    if [ -z "$worktree_path" ]; then
      echo "PATH is required" >&2
      exit 2
    fi
    shift

    branch=""
    start_point=""
    init_submodules=1
    init_mode="normal"
    init_jobs=""

    while [ "$#" -gt 0 ]; do
      case "${1:-}" in
        --branch|-b)
          shift
          if [ $# -eq 0 ] || [ -z "${1:-}" ]; then
            echo "--branch requires a value" >&2
            exit 2
          fi
          branch="$1"
          ;;
        --branch=*)
          branch=${1#--branch=}
          ;;
        --start-point)
          shift
          if [ $# -eq 0 ] || [ -z "${1:-}" ]; then
            echo "--start-point requires a value" >&2
            exit 2
          fi
          start_point="$1"
          ;;
        --start-point=*)
          start_point=${1#--start-point=}
          ;;
        --no-submodules)
          init_submodules=0
          ;;
        --no-fetch|--submodule-no-fetch)
          init_mode="no-fetch"
          ;;
        --fetch-fallback|--submodule-fetch-fallback)
          init_mode="fetch-fallback"
          ;;
        --jobs|--submodule-jobs)
          option_name="$1"
          shift
          if [ $# -eq 0 ] || [ -z "${1:-}" ]; then
            echo "$option_name requires a value" >&2
            exit 2
          fi
          init_jobs="$1"
          ;;
        --jobs=*|--submodule-jobs=*)
          init_jobs=${1#*=}
          ;;
        --*)
          echo "unknown linked worktree add option: $1" >&2
          exit 2
          ;;
        *)
          if [ -n "$start_point" ]; then
            echo "unexpected linked worktree add argument: $1" >&2
            exit 2
          fi
          start_point="$1"
          ;;
      esac
      shift
    done

    if [ -n "$branch" ] && [ -n "$start_point" ]; then
      git worktree add -b "$branch" "$worktree_path" "$start_point"
    elif [ -n "$branch" ]; then
      git worktree add -b "$branch" "$worktree_path"
    elif [ -n "$start_point" ]; then
      git worktree add "$worktree_path" "$start_point"
    else
      git worktree add "$worktree_path"
    fi

    if [ "$init_submodules" -eq 1 ]; then
      run_init_all_in_worktree "$worktree_path" "$init_mode" "$init_jobs"
    fi
    ;;

  remove-linked-worktree)
    worktree_path="${1:-}"
    if [ -z "$worktree_path" ]; then
      echo "PATH is required" >&2
      exit 2
    fi
    shift

    force=0
    while [ "$#" -gt 0 ]; do
      case "${1:-}" in
        --force|-f)
          force=1
          ;;
        --*)
          echo "unknown linked worktree remove option: $1" >&2
          exit 2
          ;;
        *)
          echo "unexpected linked worktree remove argument: $1" >&2
          exit 2
          ;;
      esac
      shift
    done

    if [ "$force" -eq 1 ]; then
      git worktree remove --force "$worktree_path"
    else
      git worktree remove "$worktree_path"
    fi
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

  *)
    echo "Unknown action: $action" >&2
    exit 2
    ;;
esac
