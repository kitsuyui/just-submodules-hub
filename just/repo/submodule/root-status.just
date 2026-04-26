root_status_source_dir := source_directory()

# Hide all submodule changes from the parent repository status.
hide REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{root_status_source_dir}}/../../../scripts/repo/run-with-hooks.sh" submodule-root-status-hide "{{REPO}}"

# Show submodule changes in the parent repository status again.
show REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{root_status_source_dir}}/../../../scripts/repo/run-with-hooks.sh" submodule-root-status-show "{{REPO}}"

# Show whether submodule changes are hidden from the parent repository status.
visibility REPO="":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{root_status_source_dir}}/../../../scripts/repo/run-with-hooks.sh" submodule-root-status-visibility "{{REPO}}"
