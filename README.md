# just-submodules-hub

Reusable `just` modules and scripts for Git submodule hub operations.

This repository is designed to be consumed by submodule-hub repositories, typically generated from [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub).

## Start Here

For setup philosophy, directory layout, and bootstrap flow, see:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)

## Scope

This repository should contain shared, reusable logic:

- `just` modules for submodule operations
- helper scripts for those modules
- shared behavior that should be consistent across hubs

Consumers should normally import `just/index.just`, which aggregates the shared modules.

## Requirements

This repository assumes the following tools are available:

- [`just`](https://github.com/casey/just) to run the shared recipes
- [`git`](https://git-scm.com/) to manage submodules
- [`uv`](https://github.com/astral-sh/uv) to run the bundled Python utilities

On macOS, install them with Homebrew:

```sh
brew install just git uv
```

If you use GitHub-related commands such as `just github::repos::public::create`, `just github::repos::private::create`, `just github::repos::list`, `just github::prs::list`, or `just github::issues::list`, install the GitHub CLI as well:

```sh
brew install gh
```

Make sure `gh auth login` has been completed before using those commands.

## Command Structure

Shared commands are grouped into two top-level namespaces:

- `repo`: local hub operations such as submodule management, cataloging, and opening repositories
- `github`: GitHub-facing operations such as repository listing, PR/issue inspection, branch protection, and merge policy

Examples:

```sh
just repo::submodule::default-branch::sync-all
just repo::submodule::default-branch::sync-all --token-env SUBMODULES_TOKEN --no-prefilter
just repo::submodule::init-all
just repo::branches::cleanup
just repo::worktrees::branches::cleanup
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide just-submodules-hub
just repo::submodule::worktree::reconcile just-submodules-hub
just repo::submodule::worktrees::reconcile
just repo::submodule::hooks::install
just repo::submodule::hooks::install --dry-run --format table
just repo::linked-worktrees::list
just repo::linked-worktrees::add ../hub-feature --branch feature/hub --fetch-fallback
just repo::linked-worktrees::hooks::install
just repo::linked-worktrees::cleanup --path-glob '../hub-*'
just repo::linked-worktrees::sync::plan --format jsonl
just repo::linked-worktrees::sync::apply --format jsonl
just repo::worktrees::reconcile
just repo::submodule::every "git status --short"
just repo::submodule::hooks::install --format jsonl --jobs 8
just repo::submodule::managed::list kitsuyui private
just repo::catalog::languages::python::list
just repo::catalog::languages::python::every "uv run pytest"
just repo::open::tools::codex::open just-submodules-hub
just github::repos::list
just github::prs::summaries::show
just github::issues::summaries::show
just github::branch-protection::all::status
just github::merge-policy::squash::all::status
```

For command discovery, use:

```sh
just --list --list-submodules
```

To inspect only the canonical command tree without compatibility aliases, use:

```sh
just --list --list-submodules --no-aliases
```

Detailed command guides live under [`docs/`](docs/README.md):

- [`docs/repo/`](docs/repo/README.md)
- [`docs/github/`](docs/github/README.md)
- [`docs/command-naming.md`](docs/command-naming.md)
- [`docs/repo/hooks.md`](docs/repo/hooks.md): `before-` / `after-` hook mechanism for repo recipes

The recommended entrypoint is:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/index.just"
```

The namespace guides in [`docs/`](docs/README.md) are the canonical reference. Follow [`docs/command-naming.md`](docs/command-naming.md) when adding or renaming recipes. Keep consumer-specific README customization in the consumer repository, not here.

### Submodule Status Noise

Consumer hubs usually treat each submodule as an independent working repository. For that workflow, `repo::submodule::add` and `repo::submodule::init-all` set `submodule.<name>.ignore=all` in the consumer repository's local `.git/config` by default.

You can also manage that setting explicitly with:

```sh
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide owner/repo
just repo::submodule::root-status::visibility
```

This uses Git's local `submodule.<name>.ignore` setting in the consumer repository's `.git/config`.

- `add` and `init-all` default submodules to `ignore=all` for parent status noise reduction.
- `root-status::hide` sets `ignore=all`, suppressing modified, untracked, and `new commits` noise in the parent repository status.
- `root-status::show` clears the local ignore setting and restores visibility.
- `root-status::visibility` reports `hidden` or `visible`.
- `pointers::commit` still stages and commits intentional gitlink updates by comparing the recorded gitlink with the submodule `HEAD`.
- Deprecated aliases such as `hide-root-status-changes`, `hide-worktree-changes`, `hide-all-changes`, `ignore-dirty-*`, and `ignore-all-*` remain available for compatibility.

### Sync Options

- `scripts/repo/run-action.sh sync-repo-default-branch <repo|owner/repo|repo/github.com/owner/repo> --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --jobs 8 --no-prefilter --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --final-submodule-update`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --token-env SUBMODULES_TOKEN --no-prefilter`
- `repo::submodule::default-branch::sync-all` uses Python + `tqdm` with one transient progress bar
- Use `repo::submodule::default-branch::sync-all` when the goal is to move managed submodules to their default branches.
- Pass `--token-env <ENV>` in CI when GitHub submodule URLs need temporary HTTPS token authentication. The named environment variable must contain a token with `contents: read` access to every target submodule repository. The command restores tokenized parent submodule URLs and initialized submodule origins after success or failure.
- Use `repo::submodule::worktrees::reconcile` when the goal is to preserve topic/PR branch context and clean up only states that can be settled non-destructively.
- Use `repo::worktrees::reconcile` when the root repository and all submodule worktrees should be made fresh together.

### Branch Cleanup

Use these commands to delete local or remote branches whose pull requests are already merged:

```sh
just repo::branches::cleanup
just repo::submodule::branches::cleanup --format jsonl
just repo::worktrees::branches::cleanup --apply
```

Branch cleanup is dry-run by default. It skips default branches, current branches, and branches with open pull requests. Pass `--apply` to delete candidates, and use `--no-local` or `--no-remote` to limit the target.
Remote branch cleanup only includes merged pull requests authored by the authenticated GitHub user by default. Pass `--include-non-owner-remote` only when branches from merged pull requests authored by other users are intentionally in scope.
Skipped branches are hidden by default; pass `--include-skipped` when you want to audit every branch decision.

### Submodule Worktree Reconciliation

Use these commands when submodules may be on a mix of default branches, topic branches, pull request branches, or detached HEADs:

```sh
just repo::submodule::worktree::reconcile owner/repo
just repo::submodule::worktrees::reconcile
just repo::submodule::worktrees::reconcile --format jsonl
just repo::submodule::worktrees::reconcile --format table --jobs 8
just repo::worktrees::reconcile
```

The reconciler keeps pointer commits separate from worktree cleanup. It only runs non-destructive Git operations such as `pull --ff-only`, normal `switch`, and `fetch`; intentional gitlink updates still belong to `repo::submodule::pointers::commit`.

The aggregate command reports one row per worktree with `status`, `action`, branch, PR number, dirty state, and message. It uses a shared progress-bar and parallel execution helper, accepts a jobs value, and exits with `1` only when one or more worktrees fail. Skipped states, such as an open PR branch, are reported but are not treated as failures.

By default, reconciliation uses the same owner-level GraphQL default-branch prefilter as `default-branch::sync-all`. Submodules already on the remote default branch HEAD are reported as `noop` without running per-repository `pull`.

`repo::submodule::every` uses the same batch foundation for arbitrary shell commands:

```sh
just repo::submodule::every ls
just repo::submodule::every "git status --short"
just repo::submodule::every ls --format jsonl --jobs 8
just repo::catalog::languages::python::every "uv run pytest" --format jsonl --jobs 8
```

By default, it prints simple per-submodule command output. Use `--format table`, `--format tsv`, or `--format jsonl` when you need per-submodule `stdout`, `stderr`, and exit code records. The `catalog::languages::*::every` commands use the corresponding language marker as a prefilter before running the same batch command runner. The overall command exits non-zero when any submodule command fails.

### Shallow Submodule Setup

`repo::submodule::add` records new submodules with `shallow = true` in `.gitmodules` and sets the local parent-status visibility to hidden.
When a hub is cloned later, `git submodule update --recommend-shallow` can use that hint to keep initial setup lighter.
Use `repo::submodule::init-all` to initialize registered submodules recursively with recommended shallow behavior and to default registered submodules to hidden parent status.
Pass a jobs value explicitly, use `--jobs <n>`, or set Git's `submodule.fetchJobs`; otherwise the command uses the local CPU count when available.
Use `--no-fetch` to initialize from already available local objects without contacting remotes. Use `--fetch-fallback` to try the no-fetch path first and retry with normal fetching if that update fails.

## Development

This repository uses [lefthook](https://github.com/evilmartians/lefthook) to run CI checks locally before commits and pushes.

Install lefthook and set up the hooks once:

```sh
lefthook install
```

The following hooks are configured:

- **pre-commit**: runs `just typecheck` (mypy static type checking)
- **pre-push**: runs `just typecheck` and `just test` (mypy + pytest unit and integration tests)

CI still runs the full suite (formatting, lint, typecheck, and tests) on every pull request and push to main.

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
