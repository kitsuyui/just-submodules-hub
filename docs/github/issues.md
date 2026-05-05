# `github::issues`

Use `github::issues` to inspect issues across managed repositories.

## Intent

Use these commands when you want a quick view of issue activity across the repositories managed by the hub.

## Examples

```sh
just github::issues::list
just github::issues::list closed
just github::issues::summaries::show
just github::issues::summaries::show all
```

## Deprecated aliases

The flat summary command remains available as a compatibility alias. Prefer the primary command above.

| Deprecated alias | Use instead |
| --- | --- |
| `summary` | `summaries::show` |

## States

The shared recipes accept the same issue states that the bundled scripts support:

- `open`
- `closed`
- `all`
