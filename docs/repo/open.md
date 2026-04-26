# `repo::open`

Use `repo::open` to resolve a managed repository path and open it in a local tool.

## Intent

Use these commands when you want to jump from a managed repository name to the local checkout in your preferred tool.

## Examples

```sh
just repo::open::tool codex <repo|owner/repo|repo/github.com/owner/repo>
just repo::open::tools::claude::open <repo|owner/repo|repo/github.com/owner/repo>
just repo::open::tools::codex::open <repo|owner/repo|repo/github.com/owner/repo>
just repo::open::tools::vscode::open <repo|owner/repo|repo/github.com/owner/repo>
just repo::open::tools::iterm2::open <repo|owner/repo|repo/github.com/owner/repo>
```

## Notes

- `tool` is the generic primitive.
- Short names work only when they resolve to exactly one managed repository.
- This namespace is intentionally local-machine oriented.

## Deprecated aliases

The previous flat tool commands remain available as compatibility aliases. Prefer the primary commands above.

| Deprecated alias | Use instead |
| --- | --- |
| `claude` | `tools::claude::open` |
| `codex` | `tools::codex::open` |
| `vscode` | `tools::vscode::open` |
| `iterm2` | `tools::iterm2::open` |
