# `github::repos`

GitHub repository creation and listing belong under `github::repos`.

## Intent

Use these commands when you want to list repositories on GitHub or create a new repository before adding it to the hub.

The create commands are the canonical bootstrap path for a repository managed by
a submodule hub. They create the GitHub repository first and then clone it
directly into `repo/github.com/<owner>/<repo>` as a submodule. Scaffold the
project only after this command succeeds; do not create a persistent sibling
checkout such as `~/project-name` as an intermediate workspace.

## Examples

```sh
just github::repos::list
just github::repos::owner::list kitsuyui
just github::repos::public::create kitsuyui/new-repo
just github::repos::private::create kitsuyui/new-private-repo
```

Repository creation and submodule registration are separate hook-wrapped
actions within the same command. Consumer `before-add-repo` and
`after-add-repo` hooks therefore run normally, including identity selection and
checkout-local configuration. If submodule registration fails after GitHub
repository creation, rerun the same command: the existing repository is reused
and registration is retried.

## Requirements

- `gh` must be installed
- `gh auth login` must be completed
- creating repositories requires the necessary GitHub permissions

## Deprecated aliases

The following aliases remain available for compatibility. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `list-owner` | `owner::list` |
| `create-public` | `public::create` |
| `create-private` | `private::create` |
