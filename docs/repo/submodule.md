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
just repo::submodule::hide-worktree-changes
just repo::submodule::hide-worktree-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::show-worktree-changes
just repo::submodule::show-worktree-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::worktree-changes-visibility
just repo::submodule::worktree-changes-visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::hide-all-changes
just repo::submodule::hide-all-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::show-all-changes
just repo::submodule::show-all-changes <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::all-changes-visibility
just repo::submodule::all-changes-visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::list-managed
just repo::submodule::list-unmanaged
just repo::submodule::every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- Short names work only when they resolve to exactly one managed repository.
- `commit-pointers` stages and commits only gitlink updates.
- `hide-worktree-changes` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `hide-worktree-changes` without arguments updates all managed submodules.
- `hide-worktree-changes <repo>` targets only the resolved managed submodule.
- `hide-worktree-changes` hides local worktree dirt, but does not hide `new commits`.
- `hide-all-changes` hides both local dirt and `new commits` in the parent repository status.
- `worktree-changes-visibility` and `all-changes-visibility` report `hidden` or `visible`.
- Legacy `ignore-dirty-*` and `ignore-all-*` aliases remain available for compatibility.
