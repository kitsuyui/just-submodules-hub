github_merge_policy_squash_source_dir := source_directory()

mod all "squash/all.just"

# Show whether squash merge is allowed for one repository.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_source_dir}}/../../../scripts/github/repository-merge-policy.sh" status squash "{{REPO}}"

# Allow squash merge for one repository.
enable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_source_dir}}/../../../scripts/github/repository-merge-policy.sh" enable squash "{{REPO}}"

# Disallow squash merge for one repository.
disable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_source_dir}}/../../../scripts/github/repository-merge-policy.sh" disable squash "{{REPO}}"
