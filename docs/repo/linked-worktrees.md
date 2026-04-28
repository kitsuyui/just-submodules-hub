# `repo::linked-worktrees`

Use `repo::linked-worktrees` for Git linked worktrees that belong to the parent repository.

## Intent

This namespace is intentionally separate from `repo::worktrees`. The existing `repo::worktrees` namespace reconciles the root checkout together with managed submodule worktrees. `repo::linked-worktrees` is for `git worktree` entries of the parent repository itself.

## Examples

```sh
just repo::linked-worktrees::list
just repo::linked-worktrees::list --format jsonl
just repo::linked-worktrees::list --format tsv
just repo::linked-worktrees::add ../hub-feature --branch feature/hub --start-point main
just repo::linked-worktrees::add ../hub-feature --fetch-fallback --jobs 4
just repo::linked-worktrees::add ../hub-feature --no-submodules
just repo::linked-worktrees::remove ../hub-feature
just repo::linked-worktrees::hooks::install
just repo::linked-worktrees::reset ../hub-feature
just repo::linked-worktrees::reset ../hub-feature --apply
just repo::linked-worktrees::cleanup --path-glob '../hub-*'
just repo::linked-worktrees::cleanup --path-glob '../hub-*' --apply --drop-branch
just repo::linked-worktrees::sync::plan
just repo::linked-worktrees::sync::plan --format jsonl
just repo::linked-worktrees::sync::apply
just repo::linked-worktrees::sync::apply --format jsonl
```

## Notes

- `list` is a read-only wrapper around `git worktree list --porcelain`.
- Output formats are `table`, `tsv`, and `jsonl`.
- The command reports the main worktree and linked worktrees because that is the shape returned by Git's porcelain output.
- `add` wraps `git worktree add` and initializes submodules in the new worktree unless `--no-submodules` is passed.
- `add --no-fetch` and `add --fetch-fallback` pass the corresponding low-fetch behavior to `repo::submodule::init-all` in the new worktree.
- `remove` is a thin wrapper around `git worktree remove`; pass `--force` only when Git's normal safety check should be overridden.
- `hooks::install` installs a pre-push guard that blocks pushes of local-only `worktree/*` branches. Existing hooks are not overwritten; a sample hook is written instead.
- `reset` defaults to dry-run. `reset --apply` backs up the current `HEAD` to `stash/<worktree>/<timestamp>` before resetting the current branch to the target, which defaults to `origin/<default-branch>`. Dirty worktrees are skipped.
- `cleanup` defaults to dry-run and requires `--path-glob`. It only targets worktrees whose planner action is `retire-contained` or `retire-merged-pr`; branch deletion requires `--drop-branch`.
- `sync::plan` is read-only. It reports the default safe decision for each worktree without rebasing, switching, deleting, or removing anything.
- The sync planner skips dirty worktrees, detached worktrees, locked worktrees, prunable worktrees, and open non-draft pull request branches.
- The sync planner treats missing `gh` or unavailable pull request metadata conservatively and skips topic branches rather than assuming they are private WIP.
- `sync::apply` runs only actions that `sync::plan` reports as `planned`. Skipped and failed plans remain unchanged in the output.
- `sync::apply` does not force-push, delete branches, or remove worktrees.
- Follow-up commands for cleanup and hooks should build on this namespace after their safety behavior is specified.
