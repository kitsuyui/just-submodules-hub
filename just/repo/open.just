repo_open_source_dir := source_directory()

# Open a managed repository in the selected tool.
tool TOOL REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_source_dir}}/../../scripts/repo/run-with-hooks.sh" open-repo "{{TOOL}}" "{{REPO}}"

# Open a managed repository in Codex.
codex REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && just repo open tool codex "{{REPO}}"

# Open a managed repository in VS Code.
vscode REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && just repo open tool vscode "{{REPO}}"

# Open a managed repository in iTerm2.
iterm2 REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && just repo open tool iterm2 "{{REPO}}"
