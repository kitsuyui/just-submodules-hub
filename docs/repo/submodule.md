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
just repo::submodule::hide-root-status-changes
just repo::submodule::hide-root-status-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::show-root-status-changes
just repo::submodule::show-root-status-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status-changes-visibility
just repo::submodule::root-status-changes-visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::hide-worktree-changes
just repo::submodule::hide-worktree-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::hide-all-changes
just repo::submodule::hide-all-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::list-managed
just repo::submodule::list-unmanaged
just repo::submodule::every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- Short names work only when they resolve to exactly one managed repository.
- `commit-pointers` stages and commits only gitlink updates.
- `hide-root-status-changes` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `hide-root-status-changes` without arguments updates all managed submodules.
- `hide-root-status-changes <repo>` targets only the resolved managed submodule.
- `hide-root-status-changes` sets `ignore=all`, hiding local dirt and `new commits` in the parent repository status.
- `root-status-changes-visibility` reports `hidden` or `visible`.
- `commit-pointers` compares the recorded gitlink with the submodule `HEAD`, so intentional gitlink updates remain committable while root status is hidden.
- Legacy `hide-worktree-changes`, `hide-all-changes`, `ignore-dirty-*`, and `ignore-all-*` aliases remain available for compatibility.
