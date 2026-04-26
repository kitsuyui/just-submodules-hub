# Command Naming

This project treats `just` recipe names as a stable command tree.

## Primary Rule

Canonical commands should follow this shape:

```text
<namespace>::<resource>[::<resource>...]::<verb>
```

The command path should describe a resource tree first, then put the action at the leaf.

Examples:

```sh
just repo::submodule::default-branch::sync-all
just repo::submodule::pointers::commit
just repo::submodule::managed::list
just github::repos::public::create
just github::branch-protection::all::rulesets::cleanup
```

## Design Principles

- Prefer a clear resource tree over natural English phrasing.
- Keep the verb at the end of the command path.
- Use singular resource names when the command targets one logical resource, such as `ruleset::cleanup`.
- Use plural resource names when the node represents a collection as the resource itself, such as `repos` or `rulesets`.
- Keep established top-level namespaces small. Current primary namespaces are `repo` and `github`.
- Add a nested module when a command name would otherwise combine multiple resources or move the verb away from the leaf.

## Compatibility Aliases

When renaming an existing command:

1. Add the new canonical command first.
2. Keep the old command as a `just` alias.
3. Add a code comment near the alias that marks it as deprecated compatibility.
4. Update internal calls, tests, and documentation examples to use the canonical command.
5. Document the alias mapping in the relevant namespace guide.

Deprecated aliases are compatibility shims, not examples for new commands. `just` aliases do not emit runtime deprecation warnings, so the deprecation note lives in the justfile comments and documentation.

Use this to inspect the full command tree:

```sh
just --list --list-submodules
```

Use this when reviewing only canonical commands:

```sh
just --no-aliases --list --list-submodules
```

## Anti-Patterns

Avoid names that flatten the resource tree into one compound command:

| Avoid | Prefer |
| --- | --- |
| `repo::submodule::sync-default-branch` | `repo::submodule::default-branch::sync` |
| `repo::submodule::sync-all-default-branch` | `repo::submodule::default-branch::sync-all` |
| `repo::submodule::commit-pointers` | `repo::submodule::pointers::commit` |
| `github::repos::create-public` | `github::repos::public::create` |
| `github::branch-protection::cleanup-ruleset` | `github::branch-protection::ruleset::cleanup` |
| `github::branch-protection::cleanup-classic-all` | `github::branch-protection::all::classic::cleanup` |

## Review Checklist

Before adding or changing a recipe:

- Does the command path read as a namespace/resource tree?
- Is the verb the final segment?
- Would any segment become clearer as a nested module?
- If this replaces an existing command, is the old command kept as a deprecated alias?
- Do docs and tests use the canonical command instead of the alias?
