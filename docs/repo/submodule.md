# `repo::submodule`

Local submodule operations belong under the `repo::submodule` namespace.

## Intent

Use these commands when you want to add, remove, sync, or inspect managed submodules from the parent hub repository.

## Examples

```sh
just repo::submodule::add <owner>/<repo>
just repo::submodule::remove <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::init-all
just repo::submodule::init-all <jobs>
just repo::submodule::default-branch::sync <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::default-branch::sync-all
just repo::submodule::pointers::commit
just repo::submodule::root-status::hide
just repo::submodule::root-status::hide <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::show
just repo::submodule::root-status::show <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::root-status::visibility
just repo::submodule::root-status::visibility <repo|owner/repo|repo/github.com/owner/repo>
just repo::submodule::managed::list
just repo::submodule::unmanaged::list
just repo::submodule::every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- `add` records new submodules with `shallow = true` in `.gitmodules`; later setup commands that use `git submodule update --recommend-shallow` can then avoid fetching full history.
- `init-all` initializes registered submodules with `--recursive --recommend-shallow`. Pass `jobs` explicitly, or configure `submodule.fetchJobs`; otherwise the command uses the local CPU count when available.
- Short names work only when they resolve to exactly one managed repository.
- `pointers::commit` stages and commits only gitlink updates.
- `root-status::hide` changes the consumer repository's local `.git/config`, not `.gitmodules`.
- `root-status::hide` without arguments updates all managed submodules.
- `root-status::hide <repo>` targets only the resolved managed submodule.
- `root-status::hide` sets `ignore=all`, hiding local dirt and `new commits` in the parent repository status.
- `root-status::visibility` reports `hidden` or `visible`.
- `pointers::commit` compares the recorded gitlink with the submodule `HEAD`, so intentional gitlink updates remain committable while root status is hidden.

## Deprecated aliases

The following aliases remain available for compatibility and emit a warning. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `sync-default-branch` | `default-branch::sync` |
| `sync-all-default-branch` | `default-branch::sync-all` |
| `commit-pointers` | `pointers::commit` |
| `list-managed` | `managed::list` |
| `list-unmanaged` | `unmanaged::list` |
| `hide-root-status-changes` | `root-status::hide` |
| `hide-worktree-changes` | `root-status::hide` |
| `hide-all-changes` | `root-status::hide` |
| `ignore-all-on` | `root-status::hide` |
| `show-root-status-changes` | `root-status::show` |
| `show-worktree-changes` | `root-status::show` |
| `show-all-changes` | `root-status::show` |
| `ignore-all-off` | `root-status::show` |
| `root-status-changes-visibility` | `root-status::visibility` |
| `worktree-changes-visibility` | `root-status::visibility` |
| `all-changes-visibility` | `root-status::visibility` |
| `ignore-all-status` | `root-status::visibility` |
| `ignore-dirty-on` | `root-status::hide` |
| `ignore-dirty-off` | `root-status::show` |
| `ignore-dirty-status` | `root-status::visibility` |
