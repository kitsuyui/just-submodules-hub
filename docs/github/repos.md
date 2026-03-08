# `github repos`

GitHub repository creation and listing belong under `github repos`.

## Intent

Use these commands when you want to list repositories on GitHub or create a new repository before adding it to the hub.

## Examples

```sh
just github repos list
just github repos list-owner kitsuyui
just github repos create-public kitsuyui/new-repo
just github repos create-private kitsuyui/new-private-repo
```

## Requirements

- `gh` must be installed
- `gh auth login` must be completed
- creating repositories requires the necessary GitHub permissions
