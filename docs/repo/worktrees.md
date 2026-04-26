# `repo::worktrees`

Use `repo::worktrees` when the root repository and managed submodules should be refreshed together.

## Intent

`repo::worktrees::reconcile` is the top-level freshness command. It reconciles the root checkout first-class alongside every managed submodule worktree, while keeping parent gitlink commits separate.

## Examples

```sh
just repo::worktrees::reconcile
just repo::worktrees::reconcile --format jsonl
just repo::worktrees::reconcile --format table --jobs 8
just repo::worktrees::reconcile --no-prefilter
just repo::worktrees::branches::cleanup
just repo::worktrees::branches::cleanup --apply
```

## Notes

- The root repository is reported as `.` in the output.
- Submodules already on the remote default branch HEAD are skipped by the GraphQL prefilter and reported as `noop`.
- Use `repo::submodule::pointers::commit` separately after reviewing intentional gitlink updates.
- Use `repo::submodule::default-branch::sync-all` instead when the goal is specifically to move submodules to their default branches.
- `branches::cleanup` defaults to dry-run and deletes only branches whose pull requests are already merged when `--apply` is passed. Remote branch cleanup only includes merged pull requests authored by the authenticated GitHub user unless `--include-non-owner-remote` is passed.
