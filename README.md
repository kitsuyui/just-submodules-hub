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

## License Scope

This repository is dedicated to the public domain under CC0-1.0.

Scope notes:

- Submodules managed by a hub are independent projects and follow their own licenses.
- Tools used with this module (for example, `just`, `git`, and `gh`) follow their respective licenses.

For onboarding philosophy and template usage, start with:

- [`template-submodules-hub`](https://github.com/kitsuyui/template-submodules-hub)
