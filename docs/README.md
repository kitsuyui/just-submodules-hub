# Documentation

Detailed usage guides for the shared `just` namespaces live here.

## Namespaces

- [`repo/`](repo/README.md): local hub operations
- [`github/`](github/README.md): GitHub-facing operations

## Design References

- [`command-naming.md`](command-naming.md): canonical `just` command naming rules

## Recommended Reading Order

1. Start with the top-level [`README.md`](../README.md).
2. Read [`command-naming.md`](command-naming.md) before adding or renaming recipes.
3. Read the namespace guide that matches the task you want to perform.
4. Use `just --list --list-submodules` in your consumer repository for full command discovery.
5. Use `just --no-aliases --list --list-submodules` when you want the canonical command tree without compatibility aliases.
6. Use `just --list repo`, `just --list repo submodule`, or similar module paths when you want a narrower list.
