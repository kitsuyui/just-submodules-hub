github_merge_policy_squash_all_source_dir := source_directory()

# Show whether squash merge is allowed for managed repositories (VISIBILITY: public/private/all).
status VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" status-all squash "{{VISIBILITY}}"

# Allow squash merge for all managed repositories.
enable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" enable-all squash "{{VISIBILITY}}"

# Disallow squash merge for all managed repositories.
disable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_squash_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" disable-all squash "{{VISIBILITY}}"
