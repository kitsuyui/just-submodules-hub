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

## Core Commands

Typical commands provided by `just/repo.just` include:

- `just add-repo <owner>/<repo>`
- `just remove-repo <owner>/<repo>`
- `just sync-repo-default-branch <owner>/<repo>`
- `just sync-all-repo-default-branch`
- `just commit-submodule-pointers`

### Sync Options

- `SYNC_VERBOSE=1`: show `up-to-date` lines for unchanged repositories
- `SYNC_JOBS=<n>`: set parallel workers for `sync-all-repo-default-branch` (default: `4`)
- `SYNC_PREFILTER_REMOTE_HEADS=0`: disable GitHub GraphQL prefilter (enabled by default)
- `SYNC_FINAL_SUBMODULE_UPDATE=1`: run extra `git submodule update --remote --rebase --recursive` after sync-all (disabled by default)
- `sync-all-repo-default-branch` uses Python + `tqdm` progress bars for GraphQL prefilter and sync phases

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
