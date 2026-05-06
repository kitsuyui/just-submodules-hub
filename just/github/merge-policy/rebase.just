github_merge_policy_rebase_source_dir := source_directory()

mod all "rebase/all.just"

# Show whether rebase merge is allowed for one repository.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_source_dir}}/../../../scripts/github/repository-merge-policy.sh" status rebase "{{REPO}}"

# Allow rebase merge for one repository.
enable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_source_dir}}/../../../scripts/github/repository-merge-policy.sh" enable rebase "{{REPO}}"

# Disallow rebase merge for one repository.
disable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_source_dir}}/../../../scripts/github/repository-merge-policy.sh" disable rebase "{{REPO}}"
