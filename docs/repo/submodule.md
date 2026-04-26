# `repo::submodule`

Local submodule operations belong under the `repo::submodule` namespace.

## Intent

Use these commands when you want to add, remove, sync, or inspect managed submodules from the parent hub repository.

## Examples

```sh
just repo::submodule::add <owner>/<repo>
just repo::submodule::remove <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::sync-default-branch <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::sync-all-default-branch
just repo::submodule::commit-pointers
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::show
just repo::submodule::root-status::show <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::visibility
just repo::submodule::root-status::visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::hide-root-status-changes
just repo::submodule::show-root-status-changes
just repo::submodule::root-status-changes-visibility
just repo::submodule::hide-worktree-changes
just repo::submodule::hide-all-changes
just repo::submodule::list-managed
just repo::submodule::list-unmanaged
just repo::submodule::every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- Short names work only when they resolve to exactly one managed repository.
- `commit-pointers` stages and commits only gitlink updates.
- `root-status::hide` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `root-status::hide` without arguments updates all managed submodules.
- `root-status::hide <repo>` targets only the resolved managed submodule.
- `root-status::hide` sets `ignore=all`, hiding local dirt and `new commits` in the parent repository status.
- `root-status::visibility` reports `hidden` or `visible`.
- `commit-pointers` compares the recorded gitlink with the submodule `HEAD`, so intentional gitlink updates remain committable while root status is hidden.
- Deprecated aliases such as `hide-root-status-changes`, `hide-worktree-changes`, `hide-all-changes`, `ignore-dirty-*`, and `ignore-all-*` remain available for compatibility and emit a warning.
