# `github::repos`

GitHub repository creation and listing belong under `github::repos`.

## Intent

Use these commands when you want to list repositories on GitHub or create a new repository before adding it to the hub.

## Examples

```sh
just github::repos::list
just github::repos::owner::list kitsuyui
just github::repos::public::create kitsuyui/new-repo
just github::repos::private::create kitsuyui/new-private-repo
```

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
