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

sync_prefilter_raw="${SYNC_PREFILTER_REMOTE_HEADS:-1}"
case "$sync_prefilter_raw" in
  0|false|FALSE|no|NO|off|OFF) sync_prefilter_remote_heads=0 ;;
  *) sync_prefilter_remote_heads=1 ;;
esac

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

  IFS="$(printf '\t')" read -r _ repo_path default_branch state switched_field updated_field <<EOF_RESULT
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

repo_owner() {
  repo_path="$1"
  repo_slug=$(repo_display_name "$repo_path")
  printf '%s\n' "${repo_slug%%/*}"
}

repo_slug() {
  repo_path="$1"
  repo_display_name "$repo_path"
}

fetch_owner_default_branch_heads() {
  owner="$1"
  output_file="$2"
  cursor=""
  # shellcheck disable=SC2016
  graphql_query='
query($owner: String!, $cursor: String) {
  repositoryOwner(login: $owner) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
      nodes {
        name
        defaultBranchRef {
          name
          target {
            ... on Commit {
              oid
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
'

  while :; do
    if [ -n "$cursor" ]; then
      response=$(gh api graphql \
        -F owner="$owner" \
        -F cursor="$cursor" \
        -f query="$graphql_query" 2>/dev/null || true)
    else
      response=$(gh api graphql \
        -F owner="$owner" \
        -f query="$graphql_query" 2>/dev/null || true)
    fi

    if [ -z "$response" ]; then
      return 1
    fi

    if ! printf '%s\n' "$response" | jq -e '.data.repositoryOwner.repositories.nodes' >/dev/null 2>&1; then
      return 1
    fi

    printf '%s\n' "$response" | jq -r --arg owner "$owner" '
      .data.repositoryOwner.repositories.nodes[]
      | select(.defaultBranchRef != null and .defaultBranchRef.target != null and .defaultBranchRef.target.oid != null)
      | "\($owner)/\(.name)\t\(.defaultBranchRef.name)\t\(.defaultBranchRef.target.oid)"
    ' >>"$output_file"

    has_next=$(printf '%s\n' "$response" | jq -r '.data.repositoryOwner.repositories.pageInfo.hasNextPage // false')
    if [ "$has_next" != "true" ]; then
      break
    fi
    cursor=$(printf '%s\n' "$response" | jq -r '.data.repositoryOwner.repositories.pageInfo.endCursor // ""')
    if [ -z "$cursor" ]; then
      break
    fi
  done

  return 0
}

build_sync_target_paths() {
  input_paths_file="$1"
  output_paths_file="$2"
  skipped_count_file="$3"

  if [ "$sync_prefilter_remote_heads" -ne 1 ]; then
    cp "$input_paths_file" "$output_paths_file"
    printf '0\n' >"$skipped_count_file"
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    cp "$input_paths_file" "$output_paths_file"
    printf '0\n' >"$skipped_count_file"
    return 0
  fi

  owners_file=$(mktemp)
  remote_heads_file=$(mktemp)

  while IFS= read -r repo_path; do
    [ -n "$repo_path" ] || continue
    repo_owner "$repo_path"
  done <"$input_paths_file" | sort -u >"$owners_file"

  prefilter_failed=0
  while IFS= read -r owner; do
    [ -n "$owner" ] || continue
    if ! fetch_owner_default_branch_heads "$owner" "$remote_heads_file"; then
      prefilter_failed=1
      break
    fi
  done <"$owners_file"

  if [ "$prefilter_failed" -ne 0 ] || [ ! -s "$remote_heads_file" ]; then
    cp "$input_paths_file" "$output_paths_file"
    printf '0\n' >"$skipped_count_file"
    rm -f "$owners_file" "$remote_heads_file"
    return 0
  fi

  skipped_count=0
  while IFS= read -r repo_path; do
    [ -n "$repo_path" ] || continue
    slug=$(repo_slug "$repo_path")
    remote_line=$(awk -F '\t' -v slug="$slug" '$1 == slug { print; exit }' "$remote_heads_file")

    if [ -z "$remote_line" ]; then
      printf '%s\n' "$repo_path" >>"$output_paths_file"
      continue
    fi

    remote_default_branch=$(printf '%s\n' "$remote_line" | cut -f2)
    remote_oid=$(printf '%s\n' "$remote_line" | cut -f3)

    if [ -z "$remote_default_branch" ] || [ -z "$remote_oid" ]; then
      printf '%s\n' "$repo_path" >>"$output_paths_file"
      continue
    fi

    local_branch=$(cd "$repo_path" && git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "DETACHED")
    local_oid=$(cd "$repo_path" && git rev-parse HEAD 2>/dev/null || true)

    if [ "$local_branch" = "$remote_default_branch" ] && [ -n "$local_oid" ] && [ "$local_oid" = "$remote_oid" ]; then
      skipped_count=$((skipped_count + 1))
      continue
    fi

    printf '%s\n' "$repo_path" >>"$output_paths_file"
  done <"$input_paths_file"

  printf '%s\n' "$skipped_count" >"$skipped_count_file"
  rm -f "$owners_file" "$remote_heads_file"
  return 0
}

sync_repo_path_to_default_branch() {
  repo_path="$1"
  if [ ! -e "$repo_path/.git" ]; then
    echo "Repository path not found: $repo_path" >&2
    exit 2
  fi

  (
    cd "$repo_path"
    current_branch=$(git symbolic-ref --quiet --short HEAD 2>/dev/null || echo "DETACHED")
    switched=0
    updated=0

    run_quiet_stdout git fetch origin --prune || return $?

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

    run_quiet_stdout git switch "$default_branch" || return $?
    before_pull=$(git rev-parse HEAD)
    run_quiet_stdout git pull --ff-only origin "$default_branch" || return $?
    after_pull=$(git rev-parse HEAD)

    if [ "$before_pull" != "$after_pull" ]; then
      updated=1
    fi

    format_sync_result "$repo_path" "$default_branch" "$switched" "$updated"
  )
}

render_progress() {
  completed="$1"
  total="$2"
  current="$3"
  width=24

  if [ "$total" -le 0 ]; then
    return 0
  fi

  filled=$((completed * width / total))
  if [ "$filled" -gt "$width" ]; then
    filled="$width"
  fi
  empty=$((width - filled))

  bar_filled=$(printf '%*s' "$filled" '' | tr ' ' '#')
  bar_empty=$(printf '%*s' "$empty" '' | tr ' ' '-')
  printf '\r[%s%s] %s/%s %s' "$bar_filled" "$bar_empty" "$completed" "$total" "$current" >&2
}

is_active_non_zombie() {
  pid="$1"
  state=$(ps -o stat= -p "$pid" 2>/dev/null | awk '{print $1}' || true)
  if [ -z "$state" ]; then
    return 1
  fi

  case "$state" in
    Z*|*Z*) return 1 ;;
    *) return 0 ;;
  esac
}

sync_all() {
  script_path="$1"
  all_paths_file=$(mktemp)
  paths_file=$(mktemp)
  results_file=$(mktemp)
  skipped_count_file=$(mktemp)
  trap 'rm -f "$all_paths_file" "$paths_file" "$results_file" "$skipped_count_file"' EXIT

  git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' >"$all_paths_file"
  if [ ! -s "$all_paths_file" ]; then
    echo "No submodule paths found in .gitmodules"
    exit 0
  fi

  : >"$paths_file"
  build_sync_target_paths "$all_paths_file" "$paths_file" "$skipped_count_file"

  skipped_count=$(cat "$skipped_count_file")
  total_all=$(wc -l <"$all_paths_file" | tr -d ' ')
  if [ -n "$skipped_count" ] && [ "$skipped_count" -gt 0 ]; then
    echo "Prefilter: skip ${skipped_count}/${total_all} repositories already at default-branch HEAD"
  fi

  if [ ! -s "$paths_file" ]; then
    echo "No repositories require sync"
    exit 0
  fi

  total=$(wc -l <"$paths_file" | tr -d ' ')
  sync_failed=0

  if [ "$sync_jobs" -le 1 ]; then
    completed=0
    while IFS= read -r repo_path; do
      [ -n "$repo_path" ] || continue
      if ! "$script_path" one-machine "$repo_path" >>"$results_file"; then
        sync_failed=1
      fi
      completed=$((completed + 1))
      render_progress "$completed" "$total" "$(repo_display_name "$repo_path")"
    done <"$paths_file"
    printf '\n' >&2
  else
    if command -v pv >/dev/null 2>&1; then
      progress_fifo=$(mktemp -u)
      mkfifo "$progress_fifo"
      pv -f -l -s "$total" <"$progress_fifo" >/dev/null &
      pv_pid=$!
      # Keep one writer FD open so pv does not see EOF between worker writes.
      exec 3>"$progress_fifo"

      if ! xargs -P "$sync_jobs" -I{} "$script_path" one-machine-with-progress "{}" "$results_file" "$progress_fifo" <"$paths_file"; then
        sync_failed=1
      fi

      exec 3>&-
      wait "$pv_pid" || true
      rm -f "$progress_fifo"
      printf '\n' >&2
    else
      xargs -P "$sync_jobs" -I{} "$script_path" one-machine "{}" <"$paths_file" >>"$results_file" &
      xargs_pid=$!
      completed=0
      last_repo=""

      while is_active_non_zombie "$xargs_pid"; do
        new_completed=$(wc -l <"$results_file" | tr -d ' ')
        if [ "$new_completed" -ne "$completed" ]; then
          completed="$new_completed"
          last_line=$(tail -n 1 "$results_file" || true)
          if [ -n "$last_line" ]; then
            IFS="$(printf '\t')" read -r _ repo_path _ _ _ _ <<EOF_LAST
$last_line
EOF_LAST
            last_repo=$(repo_display_name "$repo_path")
          fi
          render_progress "$completed" "$total" "$last_repo"
        fi
        sleep 1
      done

      if ! wait "$xargs_pid"; then
        sync_failed=1
      fi

      completed=$(wc -l <"$results_file" | tr -d ' ')
      if [ "$completed" -gt 0 ]; then
        last_line=$(tail -n 1 "$results_file" || true)
        if [ -n "$last_line" ]; then
          IFS="$(printf '\t')" read -r _ repo_path _ _ _ _ <<EOF_LAST_FINAL
$last_line
EOF_LAST_FINAL
          last_repo=$(repo_display_name "$repo_path")
        fi
      fi
      render_progress "$completed" "$total" "$last_repo"
      printf '\n' >&2
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
}

case "$action" in
  one)
    repo_path="${1:-}"
    if [ -z "$repo_path" ]; then
      echo "repo path is required" >&2
      exit 2
    fi
    sync_result=$(sync_repo_path_to_default_branch "$repo_path")
    print_sync_result "$sync_result"
    ;;
  one-machine)
    repo_path="${1:-}"
    if [ -z "$repo_path" ]; then
      echo "repo path is required" >&2
      exit 2
    fi
    sync_repo_path_to_default_branch "$repo_path"
    ;;
  one-machine-with-progress)
    repo_path="${1:-}"
    result_file="${2:-}"
    progress_fifo="${3:-}"
    if [ -z "$repo_path" ] || [ -z "$result_file" ] || [ -z "$progress_fifo" ]; then
      echo "repo path, result file and progress fifo are required" >&2
      exit 2
    fi
    if sync_repo_path_to_default_branch "$repo_path" >>"$result_file"; then
      job_status=0
    else
      job_status=$?
    fi
    printf '1\n' >"$progress_fifo"
    exit "$job_status"
    ;;
  all)
    sync_all "$0"
    ;;
  *)
    echo "Unknown sync action: $action" >&2
    exit 2
    ;;
esac
