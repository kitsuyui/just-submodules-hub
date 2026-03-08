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
- `just/github.just` for GitHub pull request queries and default-branch ruleset primitives
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

For one repository at a time, you can inspect or upsert the shared baseline ruleset on the default branch:

```sh
just default-branch-ruleset-status kitsuyui/just-submodules-hub
just default-branch-ruleset-apply kitsuyui/just-submodules-hub
just default-branch-ruleset-legacy-status kitsuyui/just-submodules-hub
just default-branch-classic-protection-status kitsuyui/just-submodules-hub
```

The managed baseline currently enforces:

- `pull_request`
- `non_fast_forward`
- `deletion`

`default-branch-ruleset-status` prints JSON so you can inspect missing rule types and `pull_request` parameter drift before applying changes.

If older rulesets such as `protect-main` remain, inspect them first:

```sh
just default-branch-ruleset-legacy-status kitsuyui/just-submodules-hub
```

This command reports which legacy rulesets are deletable. A legacy ruleset is only deletable when its rules are already covered by the remaining active rulesets. If it still carries uncovered rules such as `required_linear_history`, keep it and review it manually.

To delete a redundant legacy ruleset by id or name:

```sh
just default-branch-ruleset-delete-if-redundant kitsuyui/just-submodules-hub protect-main
```

Classic branch protection can also be inspected and deleted conservatively:

```sh
just default-branch-classic-protection-status kitsuyui/just-submodules-hub
just default-branch-classic-protection-delete-if-redundant kitsuyui/just-submodules-hub
```

The classic delete command only proceeds when the classic protection contains no extra settings outside the managed baseline. If classic protection still carries settings such as `required_status_checks`, it is reported for manual review and is not deleted automatically.

For managed repositories in bulk, the shared workflow is split into four explicit phases:

```sh
just default-branch-baseline-status-all
just default-branch-baseline-apply-all
just default-branch-baseline-cleanup-rulesets-all
just default-branch-baseline-cleanup-classic-all
```

These commands default to `public` repositories. Pass `private` or `all` explicitly when needed.

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
