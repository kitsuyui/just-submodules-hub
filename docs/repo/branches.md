# `repo::branches`

Use `repo::branches` to clean up branches in the root repository.

## Intent

`repo::branches::cleanup` finds local and remote branches whose pull requests are already merged and deletes them only when explicitly requested.

## Examples

```sh
just repo::branches::cleanup
just repo::branches::cleanup --format jsonl
just repo::branches::cleanup --apply
just repo::branches::cleanup --no-remote
just repo::branches::cleanup --include-skipped
just repo::worktrees::branches::cleanup --include-non-owner-remote
```

## Notes

- The default mode is dry-run. Use `--apply` to delete branches.
- Default, current, and open-PR branches are skipped.
- Skipped branches are hidden by default so dry-run output focuses on delete candidates. Use `--include-skipped` to audit every branch decision.
- Both local and `origin` remote branches are checked by default.
- Remote branch cleanup only includes merged pull requests authored by the authenticated GitHub user by default. Use `--include-non-owner-remote` when you intentionally want to include remote branches from merged pull requests authored by other users.
- Use `--no-local` or `--no-remote` to narrow the cleanup target.
- Use `repo::submodule::branches::cleanup` for managed submodules only.
- Use `repo::worktrees::branches::cleanup` for the root repository and all managed submodules.

## Scope of `repo::worktrees::branches::cleanup`

Despite the `worktrees` segment in the recipe path, this command operates on the **root repository plus every managed submodule** — that is, every working tree this hub knows about via `.gitmodules`. It does **not** target Git linked worktrees (the separate working trees created by `git worktree add`). To clean up branches under linked worktrees, use the linked-worktree-aware tooling under `repo::linked-worktrees::*` instead.

The naming follows the loose sense of "all working trees managed by this hub" rather than Git's `git-worktree(1)` terminology.
