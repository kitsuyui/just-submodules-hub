repo_open_tools_claude_source_dir := source_directory()

# Open a managed repository in Claude Code.
open REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_tools_claude_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" open-repo claude "{{REPO}}"
