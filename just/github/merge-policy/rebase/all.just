github_merge_policy_rebase_all_source_dir := source_directory()

# Show whether rebase merge is allowed for managed repositories (VISIBILITY: public/private/all).
status VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" status-all rebase "{{VISIBILITY}}"

# Allow rebase merge for all managed repositories.
enable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" enable-all rebase "{{VISIBILITY}}"

# Disallow rebase merge for all managed repositories.
disable VISIBILITY="public":
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_merge_policy_rebase_all_source_dir}}/../../../../scripts/github/repository-merge-policy.sh" disable-all rebase "{{VISIBILITY}}"
