# `repo::submodule`

Local submodule operations belong under the `repo::submodule` namespace.

## Intent

Use these commands when you want to add, remove, sync, or inspect managed submodules from the parent hub repository.

## Examples

```sh
just repo::submodule::add <owner>/<repo>
just repo::submodule::remove <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::branches::cleanup
just repo::submodule::branches::cleanup --apply
just repo::submodule::init-all
just repo::submodule::init-all <jobs>
just repo::submodule::init-all --jobs <jobs>
just repo::submodule::init-all --no-fetch
just repo::submodule::init-all --fetch-fallback
just repo::submodule::default-branch::sync <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::default-branch::sync-all
just repo::submodule::default-branch::sync-all --token-env SUBMODULES_TOKEN --no-prefilter
just repo::submodule::pointers::commit
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::show
just repo::submodule::root-status::show <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::visibility
just repo::submodule::root-status::visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::worktree::reconcile <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::worktree::reconcile <repo|owner/repo|repo/github.com/owner/repo> --format jsonl
just repo::submodule::worktrees::reconcile
just repo::submodule::worktrees::reconcile --format tsv
just repo::submodule::worktrees::reconcile --format table --jobs 8
just repo::submodule::hooks::install
just repo::submodule::hooks::install --dry-run --format table
just repo::submodule::hooks::install --manager lefthook --format jsonl --jobs 8
just repo::submodule::managed::list
just repo::submodule::managed::list kitsuyui private
just repo::submodule::unmanaged::list
just repo::submodule::unmanaged::list kitsuyui private
just repo::submodule::every '<command>'
just repo::submodule::every '<command>' --format jsonl --jobs 8
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- `add` records new submodules with `shallow = true` in `.gitmodules`; later setup commands that use `git submodule update --recommend-shallow` can then avoid fetching full history.
- `add` also sets the new submodule to `ignore=all` in the consumer repository's local `.git/config`.
- `init-all` initializes registered submodules with `--recursive --recommend-shallow`. Pass `jobs` explicitly, use `--jobs <jobs>`, or configure `submodule.fetchJobs`; otherwise the command uses the local CPU count when available.
- `init-all --no-fetch` adds Git's `--no-fetch` mode for linked worktree and pre-fetched workflows where the needed submodule objects are already available locally.
- `init-all --fetch-fallback` tries the no-fetch update first and retries with normal fetching if that update fails.
- `init-all` also defaults registered submodules to `ignore=all` in the consumer repository's local `.git/config`.
- Short names work only when they resolve to exactly one managed repository.
- `branches::cleanup` finds branches in managed submodules whose pull requests are already merged. It is dry-run by default; pass `--apply` to delete branches. Remote branch cleanup only includes merged pull requests authored by the authenticated GitHub user unless `--include-non-owner-remote` is passed.
- `pointers::commit` stages and commits only gitlink updates.
- Parent status visibility is hidden by default after `add` and `init-all`.
- `root-status::hide` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `root-status::hide` without arguments updates all managed submodules.
- `root-status::hide <repo>` targets only the resolved managed submodule.
- `root-status::hide` sets `ignore=all`, hiding local dirt and `new commits` in the parent repository status.
- `root-status::visibility` reports `hidden` or `visible`.
- `pointers::commit` compares the recorded gitlink with the submodule `HEAD`, so intentional gitlink updates remain committable while root status is hidden.
- `default-branch::sync-all --token-env <ENV>` temporarily authenticates GitHub submodule URLs with the token stored in `ENV`. Use a token with `contents: read` access to every target submodule repository; in GitHub Actions, `GITHUB_TOKEN` works only for repositories that token is allowed to read, so cross-repository private submodules usually need a PAT or GitHub App token.
- `--token-env` rewrites parent `submodule.*.url` local config and initialized submodule `origin` URLs only for the command duration, then restores them on success or failure. Use `--no-prefilter` if the environment does not have an authenticated `gh` CLI session for the GraphQL prefilter.
- `worktree::reconcile` updates one managed submodule worktree using non-destructive Git operations.
- `worktrees::reconcile` applies the same operation to every managed submodule and aggregates the result.
- `worktrees::reconcile` accepts `--format`, `--jobs`, `--prefilter`, and `--no-prefilter`.
- Reconciliation output formats are `table`, `tsv`, and `jsonl`.
- Reconciliation uses an owner-level GraphQL default-branch prefilter by default. Submodules already on the remote default branch HEAD are reported as `noop` without running per-repository `pull`.
- Reconciliation does not commit parent gitlink changes; use `pointers::commit` separately after reviewing the result.
- `hooks::install` installs configured Git hook managers in managed submodules.
  It currently detects `lefthook.yml` / `lefthook.yaml`, `.pre-commit-config.yaml` /
  `.pre-commit-config.yml`, and `.husky/`.
- `hooks::install` is intentionally opt-in. It changes each submodule's local Git hook
  setup but does not edit repository files or commit parent gitlink changes.
- `hooks::install --dry-run` reports what would be installed without changing local
  hook configuration.
- `hooks::install --manager <name>` limits setup to one manager. Supported managers are
  `lefthook`, `pre-commit`, and `husky`.
- `hooks::install` fails a repository as ambiguous when multiple hook managers are
  configured in the same submodule, so one manager does not silently overwrite another
  manager's Git hook.
- `managed::list` without arguments lists all locally managed submodules from `.gitmodules`.
- `managed::list <owners> <visibility>` filters managed submodules by GitHub repository visibility. The visibility value can be `public`, `private`, `internal`, or `all`.
- `unmanaged::list <owners> <visibility>` uses the same owner and visibility argument order, then subtracts managed submodules from GitHub repositories.
- `every` runs an arbitrary shell command per managed submodule through the same batch execution and record rendering foundation.

## Worktree reconciliation

`worktree::reconcile` and `worktrees::reconcile` settle submodule worktrees without making parent repository commits.

The current behavior is:

- default branch already matching the remote default HEAD: report `noop` from the prefilter
- default branch needing work: run `git pull --ff-only`
- pull request branch with a merged PR: fetch the default branch, switch to it, then pull with `--ff-only`
- pull request branch with an open PR: run `git pull --ff-only` on the current branch
- pull request branch with a closed unmerged PR: report `skipped`
- detached HEAD that is an ancestor of the default branch: switch to the default branch, then pull with `--ff-only`
- detached HEAD that cannot be related to the default branch: report `skipped`
- dirty worktree: still try non-destructive operations and let Git reject unsafe updates

The aggregate report uses these statuses:

| Status | Meaning |
| --- | --- |
| `noop` | The worktree was already in the expected state. |
| `updated` | A fast-forward pull advanced the current branch. |
| `settled` | A merged PR or detached HEAD was moved back to the default branch. |
| `skipped` | The worktree was intentionally left as-is, for example because a PR is still open. |
| `failed` | A required Git operation failed. |

`worktrees::reconcile` exits with `1` when at least one row has `failed`; `skipped` rows do not make the command fail.

Use `default-branch::sync-all` when the intended outcome is to move submodules to their default branches. Use `worktrees::reconcile` when topic branches, PR branches, and detached HEADs should be interpreted before deciding whether to pull, switch, settle, or skip.

## Batch operation pattern

Submodule commands often need to run the same operation per submodule and then summarize the result. Prefer this shape for new shared commands:

1. Implement one-submodule behavior as a small worker that returns a structured result.
2. Implement all-submodule behavior by reading `.gitmodules`, applying the worker to each path, and aggregating the results.
3. Keep parent gitlink commits separate from worktree operations.
4. Report machine-readable output when useful, typically `tsv` or `jsonl`, plus a default that matches the command's most common interactive use.

The shared Python helper `just_submodules_hub.submodule_batch` contains the common parallel execution, progress bar, and record rendering pieces used by `default-branch::sync-all`, `worktrees::reconcile`, and `every`.

## Installing submodule Git hooks

`hooks::install` applies repository-local hook setup across managed submodules. It is
useful after cloning a hub, after initializing submodules, or after adding new hook
configuration such as Lefthook, pre-commit, or Husky.

Examples:

```sh
just repo::submodule::hooks::install --dry-run --format table
just repo::submodule::hooks::install --format table --jobs 8
just repo::submodule::hooks::install --manager lefthook --format jsonl
```

Detection and setup behavior:

| Manager | Detection | Setup |
| --- | --- | --- |
| `lefthook` | `lefthook.yml`, `lefthook.yaml`, `.lefthook.yml`, or `.lefthook.yaml` | `lefthook install` |
| `pre-commit` | `.pre-commit-config.yaml` or `.pre-commit-config.yml` | `pre-commit install` |
| `husky` | `.husky/` | `git config core.hooksPath .husky/_` when `.husky/_` exists, otherwise `husky` |

The aggregate report uses these statuses:

| Status | Meaning |
| --- | --- |
| `installed` | The hook manager setup command completed successfully. |
| `would-install` | `--dry-run` found a hook manager and reported the setup command. |
| `noop` | No matching hook manager was configured, or the requested manager was not configured. |
| `failed` | The setup command failed, the required command was missing, or multiple managers were configured. |

Structured output fields are `repo`, `status`, `manager`, `command`, `exit_code`,
`stdout`, and `stderr`.

## Running arbitrary commands

`every` is the generic batch command runner. It runs the command from each managed submodule root and aggregates the result.

Examples:

```sh
just repo::submodule::every ls
just repo::submodule::every "git status --short"
just repo::submodule::every ls --format jsonl --jobs 8
just repo::submodule::every "git status --short" --format table --jobs 4
```

By default, `every` prints a simple block for each submodule, similar to running a shell command over a list of directories. Use `--format table`, `--format tsv`, or `--format jsonl` for structured output.

The structured output fields are:

| Field | Meaning |
| --- | --- |
| `repo` | Managed submodule path. |
| `status` | `ok` or `failed`. |
| `exit_code` | Command exit code for that submodule. |
| `stdout` | Compacted command stdout. |
| `stderr` | Compacted command stderr. |

The command exits with `1` when one or more submodule commands fail.

## Deprecated aliases

The following aliases remain available for compatibility. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `sync-default-branch` | `default-branch::sync` |
| `sync-all-default-branch` | `default-branch::sync-all` |
| `commit-pointers` | `pointers::commit` |
| `list-managed` | `managed::list` |
| `list-unmanaged` | `unmanaged::list` |
| `hide-root-status-changes` | `root-status::hide` |
| `hide-worktree-changes` | `root-status::hide` |
| `hide-all-changes` | `root-status::hide` |
| `ignore-all-on` | `root-status::hide` |
| `show-root-status-changes` | `root-status::show` |
| `show-worktree-changes` | `root-status::show` |
| `show-all-changes` | `root-status::show` |
| `ignore-all-off` | `root-status::show` |
| `root-status-changes-visibility` | `root-status::visibility` |
| `worktree-changes-visibility` | `root-status::visibility` |
| `all-changes-visibility` | `root-status::visibility` |
| `ignore-all-status` | `root-status::visibility` |
| `ignore-dirty-on` | `root-status::hide` |
| `ignore-dirty-off` | `root-status::show` |
| `ignore-dirty-status` | `root-status::visibility` |
