repo_hub_root := "repo/github.com/kitsuyui/just-submodules-hub"

# Open a managed repository in the selected tool.
open-repo TOOL REPO:
  #!/bin/sh
  "{{repo_hub_root}}/scripts/repo/run-with-hooks.sh" open-repo "{{TOOL}}" "{{REPO}}"

# Open a managed repository in Codex.
open-repo-in-codex REPO:
  #!/bin/sh
  just open-repo codex "{{REPO}}"

# Open a managed repository in VS Code.
open-repo-in-vscode REPO:
  #!/bin/sh
  just open-repo vscode "{{REPO}}"

# Open a managed repository in iTerm2.
open-repo-in-iterm2 REPO:
  #!/bin/sh
  just open-repo iterm2 "{{REPO}}"
