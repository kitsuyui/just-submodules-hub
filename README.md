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

If you use GitHub-related commands such as `just github repos create-public`, `just github repos create-private`, `just github repos list`, or `just github prs list`, install the GitHub CLI as well:

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
just repo submodule sync-all-default-branch
just repo catalog python
just repo open codex just-submodules-hub
just github repos list
just github prs summary
just github branch-protection status-all
```

Detailed command guides live under [`docs/`](docs/README.md):

- [`docs/repo/`](docs/repo/README.md)
- [`docs/github/`](docs/github/README.md)

The recommended entrypoint is:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/index.just"
```

The namespace guides in [`docs/`](docs/README.md) are the canonical reference. Keep consumer-specific README customization in the consumer repository, not here.

### Sync Options

- `scripts/repo/run-action.sh sync-repo-default-branch <repo|owner/repo|repo/github.com/owner/repo> --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --jobs 8 --no-prefilter --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --final-submodule-update`
- `repo submodule sync-all-default-branch` uses Python + `tqdm` with one transient progress bar

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
