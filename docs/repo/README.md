# `repo` Namespace

Local hub operations are documented under this directory.

- [`submodule`](submodule.md)
- [`linked-worktrees`](linked-worktrees.md)
- [`worktrees`](worktrees.md)
- [`branches`](branches.md)
- [`catalog`](catalog.md)
- [`open`](open.md)

## Recipe Hooks

Most `repo::` recipes (and a few `github::` recipes) support optional `before-` / `after-` hooks defined as top-level recipes in the importing `justfile`. See [`hooks.md`](hooks.md) for the full list of hook-aware actions, the matching rules, and the limitations of namespaced hook recipes.
