repo_open_tools_codex_source_dir := source_directory()

# Open a managed repository in Codex.
open REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_tools_codex_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" open-repo codex "{{REPO}}"
