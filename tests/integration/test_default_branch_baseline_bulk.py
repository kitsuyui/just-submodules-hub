from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import (
    add_submodule,
    create_remote,
    init_hub,
    write_consumer_justfile,
    write_executable,
)


def test_default_branch_baseline_status_all_reports_filtered_managed_repositories(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    public_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "public-repo",
        {"README.md": "ok\n"},
    )
    private_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "private-repo",
        {"README.md": "ok\n"},
    )
    add_submodule(hub_repo, public_remote, "repo/github.com/kitsuyui/public-repo")
    add_submodule(hub_repo, private_remote, "repo/github.com/kitsuyui/private-repo")

    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/private-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/private-repo","visibility":"PRIVATE","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rulesets" ]; then
  cat <<'EOF'
[{"id":42,"name":"default-branch-baseline"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rulesets/42" ]; then
  cat <<'EOF'
{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/branches/main/protection" ]; then
  echo '{"message":"Branch not protected","status":"404"}' >&2
  exit 1
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        ["just", "github::branch-protection::all::status", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["visibility"] == "public"
    assert [item["repo"] for item in payload["repos"]] == ["kitsuyui/public-repo"]
    assert payload["repos"][0]["ruleset_status"]["baseline_compliant"] is True
    assert "status-all" in proc.stderr


def test_default_branch_baseline_status_all_skips_wiki_submodules(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    public_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "public-repo",
        {"README.md": "ok\n"},
    )
    wiki_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "public-repo.wiki",
        {"Home.md": "ok\n"},
    )
    add_submodule(hub_repo, public_remote, "repo/github.com/kitsuyui/public-repo")
    add_submodule(hub_repo, wiki_remote, "repo/github.com/kitsuyui/public-repo.wiki")

    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo.wiki" ]; then
  echo "wiki repo should have been skipped" >&2
  exit 1
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rulesets" ]; then
  cat <<'EOF'
[{"id":42,"name":"default-branch-baseline"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/rulesets/42" ]; then
  cat <<'EOF'
{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/public-repo/branches/main/protection" ]; then
  echo '{"message":"Branch not protected","status":"404"}' >&2
  exit 1
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        ["just", "github::branch-protection::all::status", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert [item["repo"] for item in payload["repos"]] == ["kitsuyui/public-repo"]
    assert "status-all" in proc.stderr


def test_default_branch_baseline_cleanup_classic_all_skips_manual_review_cases(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    repo_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "classic-repo",
        {"README.md": "ok\n"},
    )
    add_submodule(hub_repo, repo_remote, "repo/github.com/kitsuyui/classic-repo")

    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/classic-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/classic-repo","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/classic-repo/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/classic-repo/branches/main/protection" ]; then
  cat <<'EOF'
{"required_status_checks":{"strict":true},"enforce_admins":{"enabled":false},"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null,"required_linear_history":{"enabled":false},"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false},"required_conversation_resolution":{"enabled":false},"block_creations":{"enabled":false},"lock_branch":{"enabled":false},"allow_fork_syncing":{"enabled":false}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        ["just", "github::branch-protection::all::classic::cleanup", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["results"] == [
        {
            "repo": "kitsuyui/classic-repo",
            "action": "skipped",
            "reason": "manual_action_required",
            "uncovered_settings": ["required_status_checks"],
        },
    ]


def test_default_branch_baseline_apply_all_covers_update_and_create_paths(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    existing_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "existing-ruleset-repo",
        {"README.md": "ok\n"},
    )
    missing_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "missing-ruleset-repo",
        {"README.md": "ok\n"},
    )
    add_submodule(
        hub_repo,
        existing_remote,
        "repo/github.com/kitsuyui/existing-ruleset-repo",
    )
    add_submodule(
        hub_repo,
        missing_remote,
        "repo/github.com/kitsuyui/missing-ruleset-repo",
    )

    fake_bin = tmp_path / "fake-bin"
    gh_log = tmp_path / "gh.log"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
log_file="{gh_log}"
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/existing-ruleset-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/existing-ruleset-repo","visibility":"PUBLIC","defaultBranchRef":{{"name":"main"}}}}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/missing-ruleset-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/missing-ruleset-repo","visibility":"PUBLIC","defaultBranchRef":{{"name":"main"}}}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/existing-ruleset-repo/rulesets" ]; then
  cat <<'EOF'
[{{"id":42,"name":"default-branch-baseline"}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/existing-ruleset-repo/rulesets/42" ]; then
  cat <<'EOF'
{{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"pull_request","parameters":{{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}}},{{"type":"non_fast_forward"}},{{"type":"deletion"}}]}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/missing-ruleset-repo/rulesets" ]; then
  echo '[]'
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PUT" ] && [ "$4" = "repos/kitsuyui/existing-ruleset-repo/rulesets/42" ]; then
  cat > /dev/null
  echo "PUT $4" >> "$log_file"
  cat <<'EOF'
{{"id":42}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "POST" ] && [ "$4" = "repos/kitsuyui/missing-ruleset-repo/rulesets" ]; then
  cat > /dev/null
  echo "POST $4" >> "$log_file"
  cat <<'EOF'
{{"id":77}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        ["just", "github::branch-protection::all::apply", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["results"] == [
        {
            "repo": "kitsuyui/existing-ruleset-repo",
            "action": "updated",
            "ruleset_id": 42,
        },
        {
            "repo": "kitsuyui/missing-ruleset-repo",
            "action": "created",
            "ruleset_id": 77,
        },
    ]
    assert gh_log.read_text().splitlines() == [
        "PUT repos/kitsuyui/existing-ruleset-repo/rulesets/42",
        "POST repos/kitsuyui/missing-ruleset-repo/rulesets",
    ]
    assert "apply-all" in proc.stderr


def test_default_branch_baseline_cleanup_rulesets_all_covers_delete_and_skip_paths(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)
    write_consumer_justfile(hub_repo)

    deletable_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "deletable-ruleset-repo",
        {"README.md": "ok\n"},
    )
    protected_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "protected-ruleset-repo",
        {"README.md": "ok\n"},
    )
    add_submodule(
        hub_repo,
        deletable_remote,
        "repo/github.com/kitsuyui/deletable-ruleset-repo",
    )
    add_submodule(
        hub_repo,
        protected_remote,
        "repo/github.com/kitsuyui/protected-ruleset-repo",
    )

    fake_bin = tmp_path / "fake-bin"
    gh_log = tmp_path / "gh.log"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
log_file="{gh_log}"
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/deletable-ruleset-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/deletable-ruleset-repo","visibility":"PUBLIC","defaultBranchRef":{{"name":"main"}}}}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/protected-ruleset-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/protected-ruleset-repo","visibility":"PUBLIC","defaultBranchRef":{{"name":"main"}}}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/deletable-ruleset-repo/rulesets" ]; then
  cat <<'EOF'
[{{"id":100,"name":"default-branch-baseline"}},{{"id":101,"name":"legacy-covered"}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/deletable-ruleset-repo/rulesets/100" ]; then
  cat <<'EOF'
{{"id":100,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"pull_request","parameters":{{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}}},{{"type":"non_fast_forward"}},{{"type":"deletion"}}]}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/deletable-ruleset-repo/rulesets/101" ]; then
  cat <<'EOF'
{{"id":101,"name":"legacy-covered","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"deletion"}}]}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/protected-ruleset-repo/rulesets" ]; then
  cat <<'EOF'
[{{"id":200,"name":"default-branch-baseline"}},{{"id":201,"name":"legacy-manual-review"}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/protected-ruleset-repo/rulesets/200" ]; then
  cat <<'EOF'
{{"id":200,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"pull_request","parameters":{{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}}},{{"type":"non_fast_forward"}},{{"type":"deletion"}}]}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/protected-ruleset-repo/rulesets/201" ]; then
  cat <<'EOF'
{{"id":201,"name":"legacy-manual-review","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"required_status_checks"}}]}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "DELETE" ] && [ "$4" = "repos/kitsuyui/deletable-ruleset-repo/rulesets/101" ]; then
  echo "DELETE $4" >> "$log_file"
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        ["just", "github::branch-protection::all::rulesets::cleanup", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["results"] == [
        {
            "repo": "kitsuyui/deletable-ruleset-repo",
            "action": "deleted",
            "ruleset_id": 101,
            "name": "legacy-covered",
        },
        {
            "repo": "kitsuyui/protected-ruleset-repo",
            "action": "skipped",
            "name": "legacy-manual-review",
            "reason": "manual_action_required",
            "uncovered_rule_types": ["required_status_checks"],
        },
    ]
    assert gh_log.read_text().splitlines() == [
        "DELETE repos/kitsuyui/deletable-ruleset-repo/rulesets/101",
    ]
    assert "cleanup-rulesets-all" in proc.stderr
