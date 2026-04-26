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

If you use GitHub-related commands such as `just github::repos::public::create`, `just github::repos::private::create`, `just github::repos::list`, or `just github::prs::list`, install the GitHub CLI as well:

```sh
brew install gh
```

Make sure `gh auth login` has been completed before using those commands.

## Command Structure

Shared commands are grouped into two top-level namespaces:

- `repo`: local hub operations such as submodule management, cataloging, and opening repositories
- `github`: GitHub-facing operations such as repository listing, PR inspection, and branch protection

Examples:

```sh
just repo::submodule::default-branch::sync-all
just repo::submodule::init-all
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide just-submodules-hub
just repo::catalog::languages::python::list
just repo::open::tools::codex::open just-submodules-hub
just github::repos::list
just github::prs::summaries::show
just github::branch-protection::all::status
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

The recommended entrypoint is:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/index.just"
```

The namespace guides in [`docs/`](docs/README.md) are the canonical reference. Follow [`docs/command-naming.md`](docs/command-naming.md) when adding or renaming recipes. Keep consumer-specific README customization in the consumer repository, not here.

### Submodule Status Noise

If a consumer hub treats each submodule as an independent working repository, you can suppress submodule noise in the parent repository with:

```sh
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide owner/repo
just repo::submodule::root-status::visibility
```

This uses Git's local `submodule.<name>.ignore` setting in the consumer repository's `.git/config`.

- `root-status::hide` sets `ignore=all`, suppressing modified, untracked, and `new commits` noise in the parent repository status.
- `root-status::show` clears the local ignore setting and restores visibility.
- `root-status::visibility` reports `hidden` or `visible`.
- `pointers::commit` still stages and commits intentional gitlink updates by comparing the recorded gitlink with the submodule `HEAD`.
- Deprecated aliases such as `hide-root-status-changes`, `hide-worktree-changes`, `hide-all-changes`, `ignore-dirty-*`, and `ignore-all-*` remain available for compatibility.

### Sync Options

- `scripts/repo/run-action.sh sync-repo-default-branch <repo|owner/repo|repo/github.com/owner/repo> --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --jobs 8 --no-prefilter --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --final-submodule-update`
- `repo::submodule::default-branch::sync-all` uses Python + `tqdm` with one transient progress bar

### Shallow Submodule Setup

`repo::submodule::add` records new submodules with `shallow = true` in `.gitmodules`.
When a hub is cloned later, `git submodule update --recommend-shallow` can use that hint to keep initial setup lighter.
Use `repo::submodule::init-all` to initialize registered submodules recursively with recommended shallow behavior.
Pass a jobs value explicitly, or set Git's `submodule.fetchJobs`; otherwise the command uses the local CPU count when available.

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
