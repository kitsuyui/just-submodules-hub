github_merge_policy_merge_commit_all_source_dir := source_directory()

# Show whether merge commits are allowed for managed repositories (VISIBILITY: public/private/all).
status VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" status-all merge-commit "{{VISIBILITY}}"

# Allow merge commits for all managed repositories.
enable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" enable-all merge-commit "{{VISIBILITY}}"

# Disallow merge commits for all managed repositories.
disable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_merge_commit_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" disable-all merge-commit "{{VISIBILITY}}"
