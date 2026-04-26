# `github::branch-protection`

Use `github::branch-protection` to inspect or apply the shared default-branch protection baseline.

## Intent

Use these commands when you want to inspect, apply, or clean up the shared default-branch protection policy on GitHub.

## Examples

### Single Repository

```sh
just github::branch-protection::status kitsuyui/just-submodules-hub
just github::branch-protection::apply kitsuyui/just-submodules-hub
just github::branch-protection::legacy::status kitsuyui/just-submodules-hub
just github::branch-protection::ruleset::cleanup kitsuyui/just-submodules-hub protect-main
just github::branch-protection::classic::status kitsuyui/just-submodules-hub
just github::branch-protection::classic::cleanup kitsuyui/just-submodules-hub
```

### Bulk Operations

```sh
just github::branch-protection::all::status
just github::branch-protection::all::apply
just github::branch-protection::all::rulesets::cleanup
just github::branch-protection::all::classic::cleanup
```

## Managed Baseline

The current shared baseline enforces:

- `pull_request`
- `non_fast_forward`
- `deletion`

## Notes

- Bulk commands default to `public`. Pass `private` or `all` explicitly when needed.
- Bulk commands show a transient progress bar on stderr while keeping JSON results on stdout.
- Legacy or classic protection is only removed when the remaining active rules fully cover it.

## Deprecated aliases

The following aliases remain available for compatibility. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `legacy-status` | `legacy::status` |
| `cleanup-ruleset` | `ruleset::cleanup` |
| `classic-status` | `classic::status` |
| `cleanup-classic` | `classic::cleanup` |
| `status-all` | `all::status` |
| `apply-all` | `all::apply` |
| `cleanup-rulesets-all` | `all::rulesets::cleanup` |
| `cleanup-classic-all` | `all::classic::cleanup` |
