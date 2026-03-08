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

If you use GitHub-related commands such as `create-public-repo`, `create-private-repo`, `list-github-repos`, or `list-managed-prs`, install the GitHub CLI as well:

```sh
brew install gh
```

Make sure `gh auth login` has been completed before using those commands.

## Core Commands

Typical commands provided by `just/repo.just` include:

- `just add-repo <owner>/<repo>`
- `just remove-repo <owner>/<repo>`
- `just sync-repo-default-branch <owner>/<repo>`
- `just sync-all-repo-default-branch`
- `just commit-submodule-pointers`
- `just submodule-ignore-dirty-on`
- `just submodule-ignore-dirty-off`
- `just submodule-ignore-dirty-status`

Additional shared modules include:

- `just/inventory.just` for submodule inventory and cross-repository diagnostics
- `just/github.just` for GitHub pull request queries scoped to managed repositories
- `just/openers.just` for opening managed repositories in local tools

The recommended entrypoint is:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/index.just"
```

If you want local opener commands, import the optional module explicitly:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/openers.just"
```

This keeps app-specific launchers opt-in while still sharing a common `open-repo <tool> <owner>/<repo>` primitive.

For local-only submodule worktree noise control, you can toggle `ignore=dirty` for every managed submodule without editing `.gitmodules`:

```sh
just submodule-ignore-dirty-on
just submodule-ignore-dirty-status
just submodule-ignore-dirty-off
```

These commands only update the parent repository's local `.git/config`.

### Sync Options

- `scripts/repo/run-action.sh sync-repo-default-branch <owner>/<repo> --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --jobs 8 --no-prefilter --verbose`
- `scripts/repo/run-action.sh sync-all-repo-default-branch --final-submodule-update`
- `sync-all-repo-default-branch` uses Python + `tqdm` with one transient progress bar

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
