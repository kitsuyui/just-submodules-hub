# `repo::linked-worktrees`

Use `repo::linked-worktrees` for Git linked worktrees that belong to the parent repository.

## Intent

This namespace is intentionally separate from `repo::worktrees`. The existing `repo::worktrees` namespace reconciles the root checkout together with managed submodule worktrees. `repo::linked-worktrees` is for `git worktree` entries of the parent repository itself.

## Examples

```sh
just repo::linked-worktrees::list
just repo::linked-worktrees::list --format jsonl
just repo::linked-worktrees::list --format tsv
```

## Notes

- `list` is a read-only wrapper around `git worktree list --porcelain`.
- Output formats are `table`, `tsv`, and `jsonl`.
- The command reports the main worktree and linked worktrees because that is the shape returned by Git's porcelain output.
- Follow-up commands for add, remove, sync, cleanup, and hooks should build on this namespace after their safety behavior is specified.
