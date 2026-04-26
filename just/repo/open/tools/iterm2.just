repo_open_tools_iterm2_source_dir := source_directory()

# Open a managed repository in iTerm2.
open REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_open_tools_iterm2_source_dir}}/../../../../scripts/repo/run-with-hooks.sh" open-repo iterm2 "{{REPO}}"
