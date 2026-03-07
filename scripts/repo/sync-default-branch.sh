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
  paths_file=$(mktemp)
  results_file=$(mktemp)
  trap 'rm -f "$paths_file" "$results_file"' EXIT

  git config -f .gitmodules --get-regexp '^submodule\..*\.path$' | awk '{print $2}' >"$paths_file"
  if [ ! -s "$paths_file" ]; then
    echo "No submodule paths found in .gitmodules"
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
