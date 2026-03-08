# `github branch-protection`

Use `github branch-protection` to inspect or apply the shared default-branch protection baseline.

## Intent

Use these commands when you want to inspect, apply, or clean up the shared default-branch protection policy on GitHub.

## Examples

### Single Repository

```sh
just github branch-protection status kitsuyui/just-submodules-hub
just github branch-protection apply kitsuyui/just-submodules-hub
just github branch-protection legacy-status kitsuyui/just-submodules-hub
just github branch-protection cleanup-ruleset kitsuyui/just-submodules-hub protect-main
just github branch-protection classic-status kitsuyui/just-submodules-hub
just github branch-protection cleanup-classic kitsuyui/just-submodules-hub
```

### Bulk Operations

```sh
just github branch-protection status-all
just github branch-protection apply-all
just github branch-protection cleanup-rulesets-all
just github branch-protection cleanup-classic-all
```

## Managed Baseline

The current shared baseline enforces:

- `pull_request`
- `non_fast_forward`
- `deletion`

## Notes

- Bulk commands default to `public`. Pass `private` or `all` explicitly when needed.
- Legacy or classic protection is only removed when the remaining active rules fully cover it.
