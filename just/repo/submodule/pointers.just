repo_submodule_pointers_source_dir := source_directory()

# Commit only submodule pointer changes in the parent repository.
commit MESSAGE="Update submodule pointers":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{repo_submodule_pointers_source_dir}}/../../../scripts/repo/run-with-hooks.sh" commit-submodule-pointers "{{MESSAGE}}"
