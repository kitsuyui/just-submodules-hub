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


# Actions migrated to the Python entrypoint (#60 item 3, phases 1-3b).
case "$action" in
  list-github-repos-owner|list-github-repos|list-managed-repos|list-unmanaged-repos|open-repo|every-repo|grep|\
init-all-repos|sync-repo-default-branch|sync-all-repo-default-branch|reconcile-submodule-worktree|reconcile-submodule-worktrees|reconcile-worktrees|cleanup-branches|cleanup-submodule-branches|cleanup-worktree-branches|\
add-repo|remove-repo|create-public-repo|create-private-repo|commit-submodule-pointers|list-linked-worktrees|plan-linked-worktree-sync|apply-linked-worktree-sync|\
add-linked-worktree|remove-linked-worktree|install-linked-worktree-hooks|reset-linked-worktree|cleanup-linked-worktrees)
    exec uv run --project "$project_root" env PYTHONPATH="$project_root/src${PYTHONPATH:+:$PYTHONPATH}" python -m just_submodules_hub.run_action "$action" "$@"
    ;;
esac

case "$action" in
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
