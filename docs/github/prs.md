# `github::prs`

Use `github::prs` to inspect pull requests across managed repositories.

## Intent

Use these commands when you want a quick view of pull request activity across the repositories managed by the hub.

## Examples

```sh
just github::prs::list
just github::prs::list open
just github::prs::ready
just github::prs::summaries::show
just github::prs::summaries::show merged
```

## Merge-ready pull requests

`github::prs::ready` narrows the open list down to pull requests a maintainer
can merge as-is: not a draft, no merge conflict, GitHub reports the merge
state as `CLEAN`, `UNSTABLE`, or `HAS_HOOKS`, **and every check is green** —
success, neutral, or skipped. The last condition matters because
`mergeStateStatus` only covers *required* checks: a repository without
required checks reports `UNSTABLE` even while its CI is failing, so the
listing additionally inspects the full check rollup and drops pull requests
with failing or still-running checks. Pull requests that are `BEHIND` or
`BLOCKED` (e.g. missing a required review) are excluded as well. The output
keeps a `merge_state` column so the remaining judgement call stays visible.

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
