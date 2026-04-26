# `github::prs`

Use `github::prs` to inspect pull requests across managed repositories.

## Intent

Use these commands when you want a quick view of pull request activity across the repositories managed by the hub.

## Examples

```sh
just github::prs::list
just github::prs::list open
just github::prs::summaries::show
just github::prs::summaries::show merged
```

## Deprecated aliases

The previous flat summary command remains available as a compatibility alias. Prefer the primary command above.

| Deprecated alias | Use instead |
| --- | --- |
| `summary` | `summaries::show` |

## States

The shared recipes accept the same PR states that the bundled scripts support:

- `open`
- `closed`
- `merged`
- `all`
