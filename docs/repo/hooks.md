# Recipe Hooks

Some shared recipes accept user-defined `before-` and `after-` hooks that run automatically around the underlying action. This document describes how the mechanism works, where it applies, and where it does not.

## How it works

Recipes that route through `scripts/repo/run-with-hooks.sh` look up two recipe names in the importing `justfile`:

- `before-<action>`
- `after-<action>`

If a matching recipe exists, it is invoked with the same arguments as the wrapped action. The lookup uses `just --summary | grep -qx`, which matches whole lines and recognises only top-level recipe names.

```sh
# scripts/repo/run-with-hooks.sh (excerpt)
summary="$(just --summary)"
has_recipe() {
  printf '%s\n' "$summary" | tr ' ' '\n' | grep -qx "$1"
}
```

`<action>` is the canonical action name passed to `run-with-hooks.sh`. Each recipe in `just/repo/**/*.just` that goes through the wrapper passes a fixed action name, for example `add-repo`, `cleanup-branches`, or `apply-linked-worktree-sync`.

## Hooks must be top-level recipes

Because `grep -qx` requires a whole-line match, **only top-level recipe names match**. Hook recipes placed inside a namespace (for example `repo::before-add-repo`) appear in `just --summary` with their namespace prefix and are silently ignored.

Define hooks at the root of the importing `justfile`:

```just
# In your consumer's root justfile.

before-add-repo OWNER NAME:
  echo "About to add {{OWNER}}/{{NAME}}"

after-add-repo OWNER NAME:
  echo "Finished adding {{OWNER}}/{{NAME}}"
```

The arguments passed to the hook are exactly those passed to the wrapped action; consult `scripts/repo/run-with-hooks.sh` and the relevant action handler under `src/just_submodules_hub/run_action/actions/` for the canonical signatures.

## Which recipes support hooks

Hooks fire for recipes that invoke `run-with-hooks.sh`. As of this writing that includes most `repo::` recipes:

- `repo::submodule::add` (action: `add-repo`)
- `repo::submodule::remove` (action: `remove-repo`)
- `repo::submodule::init-all` (action: `init-all-repos`)
- `repo::submodule::every` (action: `every-repo`)
- `repo::submodule::hooks::install` (action: `install-submodule-hooks`)
- `repo::submodule::grep` (action: `grep`)
- `repo::submodule::pointers::commit` (action: `commit-submodule-pointers`)
- `repo::submodule::default-branch::sync` and `::sync-all` (actions: `sync-repo-default-branch`, `sync-all-repo-default-branch`)
- `repo::submodule::worktree::reconcile` and `::worktrees::reconcile` (actions: `reconcile-submodule-worktree`, `reconcile-submodule-worktrees`)
- `repo::submodule::root-status::hide` / `::show` / `::visibility`
- `repo::submodule::unmanaged::list` and `::branches::cleanup`
- `repo::worktrees::reconcile` (action: `reconcile-worktrees`)
- `repo::branches::cleanup` (action: `cleanup-branches`)
- `repo::open::tools::*::open` (action: `open-repo`)
- `repo::linked-worktrees::list` / `::add` / `::remove` / `::reset` / `::cleanup` / `::hooks::install`
- `repo::linked-worktrees::sync::plan` / `::sync::apply`
- `github::repos::list` / `::owner::list` / `::public::create` / `::private::create` (actions: `list-github-repos`, `list-github-repos-owner`, `create-public-repo`, `create-private-repo`)

Hooks do **not** fire for the following recipes, which call their backing scripts directly without the wrapper:

- `github::prs::list` and `github::prs::summaries::show`
- `github::issues::list` and `github::issues::summaries::show`
- `github::branch-protection::*`
- `github::merge-policy::*`
- `repo::catalog::duplicates::filenames`

This split is historical and may be reduced over time. Until then, do not rely on hooks for the recipes listed above.

## Failure semantics

Hook recipes run with the same shell as the rest of `just`. A non-zero exit from a `before-` hook stops execution before the wrapped action runs; a non-zero exit from an `after-` hook fails the overall invocation but does not undo the wrapped action.
