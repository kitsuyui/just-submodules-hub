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

## Core Commands

Typical commands provided by the `repo` namespace include:

- `just repo submodule add <owner>/<repo>`
- `just repo submodule remove <owner>/<repo>`
- `just repo submodule sync-default-branch <owner>/<repo>`
- `just repo submodule sync-all-default-branch`
- `just repo submodule commit-pointers`
- `just repo submodule ignore-dirty-on`
- `just repo submodule ignore-dirty-off`
- `just repo submodule ignore-dirty-status`
- `just repo catalog python`
- `just repo catalog duplicate-filenames`
- `just repo open codex <owner>/<repo>`

Additional shared modules include:

- `just/repo/catalog.just` for submodule cataloging and cross-repository diagnostics
- `just/repo/open.just` for opening managed repositories in local tools
- `just/github/index.just` for GitHub repository, pull request, and branch-protection primitives

GitHub-related recipes are exposed through the `github` module namespace:

```sh
just github repos list
just github prs list
just github branch-protection status-all
```

Repository-management recipes are exposed through the `repo` namespace:

```sh
just repo submodule list-managed
just repo submodule sync-all-default-branch
just repo catalog python
just repo open codex kitsuyui/just-submodules-hub
```

The recommended entrypoint is:

```just
import? "repo/github.com/kitsuyui/just-submodules-hub/just/index.just"
```

For local-only submodule worktree noise control, you can toggle `ignore=dirty` for every managed submodule without editing `.gitmodules`:

```sh
just repo submodule ignore-dirty-on
just repo submodule ignore-dirty-status
just repo submodule ignore-dirty-off
```

These commands only update the parent repository's local `.git/config`.

For GitHub repository creation and listing:

```sh
just github repos create-public kitsuyui/new-repo
just github repos list
```

For one repository at a time, you can inspect or upsert the shared baseline branch protection on the default branch:

```sh
just github branch-protection status kitsuyui/just-submodules-hub
just github branch-protection apply kitsuyui/just-submodules-hub
just github branch-protection legacy-status kitsuyui/just-submodules-hub
just github branch-protection classic-status kitsuyui/just-submodules-hub
```

The managed baseline currently enforces:

- `pull_request`
- `non_fast_forward`
- `deletion`

`just github branch-protection status` prints JSON so you can inspect missing rule types and `pull_request` parameter drift before applying changes.

If older rulesets such as `protect-main` remain, inspect them first:

```sh
just github branch-protection legacy-status kitsuyui/just-submodules-hub
```

This command reports which legacy rulesets are deletable. A legacy ruleset is only deletable when its rules are already covered by the remaining active rulesets. If it still carries uncovered rules such as `required_linear_history`, keep it and review it manually.

To delete a redundant legacy ruleset by id or name:

```sh
just github branch-protection cleanup-ruleset kitsuyui/just-submodules-hub protect-main
```

Classic branch protection can also be inspected and deleted conservatively:

```sh
just github branch-protection classic-status kitsuyui/just-submodules-hub
just github branch-protection cleanup-classic kitsuyui/just-submodules-hub
```

The classic delete command only proceeds when the classic protection contains no extra settings outside the managed baseline. If classic protection still carries settings such as `required_status_checks`, it is reported for manual review and is not deleted automatically.

For managed repositories in bulk, the shared workflow is split into four explicit phases:

```sh
just github branch-protection status-all
just github branch-protection apply-all
just github branch-protection cleanup-rulesets-all
just github branch-protection cleanup-classic-all
```

These commands default to `public` repositories. Pass `private` or `all` explicitly when needed.

### Sync Options

- `scripts/repo/run-action.sh sync-repo-default-branch <owner>/<repo> --verbose`
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
