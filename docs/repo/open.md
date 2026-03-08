# `repo open`

Use `repo open` to resolve a managed repository path and open it in a local tool.

## Intent

Use these commands when you want to jump from an `owner/repo` slug to the local checkout in your preferred tool.

## Examples

```sh
just repo open tool codex <owner>/<repo>
just repo open codex <owner>/<repo>
just repo open vscode <owner>/<repo>
just repo open iterm2 <owner>/<repo>
```

## Notes

- `tool` is the generic primitive.
- `codex`, `vscode`, and `iterm2` are convenience aliases.
- This namespace is intentionally local-machine oriented.
