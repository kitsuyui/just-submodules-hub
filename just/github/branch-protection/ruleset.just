github_branch_protection_ruleset_source_dir := source_directory()

# Delete one redundant legacy ruleset by id or name.
cleanup REPO IDENTIFIER:
  #!/bin/sh
  cd "{{invocation_directory()}}" && "{{github_branch_protection_ruleset_source_dir}}/../../../scripts/github/default-branch-ruleset.sh" delete-if-redundant "{{REPO}}" "{{IDENTIFIER}}"
