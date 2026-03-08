# `github prs`

Use `github prs` to inspect pull requests across managed repositories.

## Intent

Use these commands when you want a quick view of pull request activity across the repositories managed by the hub.

## Examples

```sh
just github prs list
just github prs list open
just github prs summary
just github prs summary merged
```

## States

The shared recipes accept the same PR states that the bundled scripts support:

- `open`
- `closed`
- `merged`
- `all`
