repo_open_source_dir := source_directory()

mod tools "open/tools.just"

# Open a managed repository in the selected tool.
tool TOOL REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_source_dir}}/../../scripts/repo/run-with-hooks.sh" open-repo "{{TOOL}}" "{{REPO}}"

# Deprecated compatibility aliases. Prefer tools::<tool>::open.
alias claude := tools::claude::open
alias codex := tools::codex::open
alias vscode := tools::vscode::open
alias iterm2 := tools::iterm2::open
