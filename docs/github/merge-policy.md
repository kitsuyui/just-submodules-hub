# `github::merge-policy`

Use `github::merge-policy` to inspect or apply repository merge method settings.

## Commands

Inspect whether one merge method is allowed:

```sh
just github::merge-policy::squash::status kitsuyui/just-submodules-hub
just github::merge-policy::rebase::status kitsuyui/just-submodules-hub
just github::merge-policy::merge-commit::status kitsuyui/just-submodules-hub
```

Enable or disable one merge method for one repository:

```sh
just github::merge-policy::squash::disable kitsuyui/just-submodules-hub
just github::merge-policy::rebase::enable kitsuyui/just-submodules-hub
just github::merge-policy::merge-commit::enable kitsuyui/just-submodules-hub
```

Inspect or apply the same setting to managed repositories:

```sh
just github::merge-policy::squash::all::status
just github::merge-policy::squash::all::disable
just github::merge-policy::rebase::all::disable private
just github::merge-policy::merge-commit::all::enable all
```

`all::*` accepts `public`, `private`, or `all`. The default is `public`.

## Policy

These commands map to GitHub repository options:

- `squash::enable` / `squash::disable`: `allow_squash_merge`
- `rebase::enable` / `rebase::disable`: `allow_rebase_merge`
- `merge-commit::enable` / `merge-commit::disable`: `allow_merge_commit`

Each command updates only the selected method.

## Requirements

- `gh auth status` must pass.
- The token must have permission to update repository settings for `enable` and `disable`.
