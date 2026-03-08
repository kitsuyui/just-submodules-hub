# `repo open`

Use `repo open` to resolve a managed repository path and open it in a local tool.

## Intent

Use these commands when you want to jump from a managed repository name to the local checkout in your preferred tool.

## Examples

```sh
just repo open tool codex <repo|owner/repo|repo/github.com/owner/repo>
just repo open codex <repo|owner/repo|repo/github.com/owner/repo>
just repo open vscode <repo|owner/repo|repo/github.com/owner/repo>
just repo open iterm2 <repo|owner/repo|repo/github.com/owner/repo>
```

## Notes

- `tool` is the generic primitive.
- `codex`, `vscode`, and `iterm2` are convenience aliases.
- Short names work only when they resolve to exactly one managed repository.
- This namespace is intentionally local-machine oriented.
