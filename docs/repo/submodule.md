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
just repo::submodule::ignore-dirty-on
just repo::submodule::ignore-dirty-on <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::ignore-dirty-off
just repo::submodule::ignore-dirty-off <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::ignore-dirty-status
just repo::submodule::ignore-dirty-status <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::ignore-all-on
just repo::submodule::ignore-all-on <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::ignore-all-off
just repo::submodule::ignore-all-off <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::ignore-all-status
just repo::submodule::ignore-all-status <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::list-managed
just repo::submodule::list-unmanaged
just repo::submodule::every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- Short names work only when they resolve to exactly one managed repository.
- `commit-pointers` stages and commits only gitlink updates.
- `ignore-dirty-*` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `ignore-dirty-*` without arguments updates all managed submodules.
- `ignore-dirty-* <repo>` targets only the resolved managed submodule.
- `ignore-dirty-*` hides local worktree dirt, but does not hide `new commits`.
- `ignore-all-*` hides both local dirt and `new commits` in the parent repository status.
