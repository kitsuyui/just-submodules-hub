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
```

## Notes

- `list` is a read-only wrapper around `git worktree list --porcelain`.
- Output formats are `table`, `tsv`, and `jsonl`.
- The command reports the main worktree and linked worktrees because that is the shape returned by Git's porcelain output.
- `add` wraps `git worktree add` and initializes submodules in the new worktree unless `--no-submodules` is passed.
- `add --no-fetch` and `add --fetch-fallback` pass the corresponding low-fetch behavior to `repo::submodule::init-all` in the new worktree.
- `remove` is a thin wrapper around `git worktree remove`; pass `--force` only when Git's normal safety check should be overridden.
- Follow-up commands for sync, cleanup, and hooks should build on this namespace after their safety behavior is specified.
