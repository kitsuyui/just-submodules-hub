github_merge_policy_merge_commit_source_dir := source_directory()

mod all "merge-commit/all.just"

# Show whether merge commits are allowed for one repository.
status REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_source_dir}}/../../../scripts/github/repository-merge-policy.sh" status merge-commit "{{REPO}}"

# Allow merge commits for one repository.
enable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_source_dir}}/../../../scripts/github/repository-merge-policy.sh" enable merge-commit "{{REPO}}"

# Disallow merge commits for one repository.
disable REPO:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_source_dir}}/../../../scripts/github/repository-merge-policy.sh" disable merge-commit "{{REPO}}"
