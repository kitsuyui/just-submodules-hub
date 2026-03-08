# `repo submodule`

Local submodule operations belong under the `repo submodule` namespace.

## Typical Commands

```sh
just repo submodule add <owner>/<repo>
just repo submodule remove <owner>/<repo>
just repo submodule sync-default-branch <owner>/<repo>
just repo submodule sync-all-default-branch
just repo submodule commit-pointers
just repo submodule ignore-dirty-on
just repo submodule ignore-dirty-off
just repo submodule ignore-dirty-status
just repo submodule list-managed
just repo submodule list-unmanaged
just repo submodule every '<command>'
```

## Notes

- These commands operate on the consumer repository that imports `just-submodules-hub`.
- `commit-pointers` stages and commits only gitlink updates.
- `ignore-dirty-*` changes the consumer repository's local `.git/config`, not `.gitmodules`.
