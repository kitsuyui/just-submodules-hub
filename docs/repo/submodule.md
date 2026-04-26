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
just repo::submodule::default-branch::sync <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::default-branch::sync-all
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
just repo::submodule::managed::list
just repo::submodule::unmanaged::list
just repo::submodule::every '<command>'
just repo::submodule::every '<command>' --format jsonl --jobs 8
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- `add` records new submodules with `shallow = true` in `.gitmodules`; later setup commands that use `git submodule update --recommend-shallow` can then avoid fetching full history.
- `add` also sets the new submodule to `ignore=all` in the consumer repository's local `.git/config`.
- `init-all` initializes registered submodules with `--recursive --recommend-shallow`. Pass `jobs` explicitly, or configure `submodule.fetchJobs`; otherwise the command uses the local CPU count when available.
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
- `worktree::reconcile` updates one managed submodule worktree using non-destructive Git operations.
- `worktrees::reconcile` applies the same operation to every managed submodule and aggregates the result.
- `worktrees::reconcile` accepts `--format`, `--jobs`, `--prefilter`, and `--no-prefilter`.
- Reconciliation output formats are `table`, `tsv`, and `jsonl`.
- Reconciliation uses an owner-level GraphQL default-branch prefilter by default. Submodules already on the remote default branch HEAD are reported as `noop` without running per-repository `pull`.
- Reconciliation does not commit parent gitlink changes; use `pointers::commit` separately after reviewing the result.
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
