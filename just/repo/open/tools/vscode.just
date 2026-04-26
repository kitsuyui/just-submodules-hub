repo_open_tools_vscode_source_dir := source_directory()

# Open a managed repository in VS Code.
open REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_tools_vscode_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" open-repo vscode "{{REPO}}"
