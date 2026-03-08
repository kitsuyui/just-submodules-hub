from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, init_hub, write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/github/default-branch-baseline-bulk.sh"


def test_default_branch_baseline_status_all_reports_filtered_managed_repositories(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)

    public_remote = create_remote(tmp_path, "kitsuyui", "public-repo", {"README.md": "ok\n"})
    private_remote = create_remote(tmp_path, "kitsuyui", "private-repo", {"README.md": "ok\n"})
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
        [str(SCRIPT), "status-all", "public"],
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


def test_default_branch_baseline_cleanup_classic_all_skips_manual_review_cases(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)

    repo_remote = create_remote(tmp_path, "kitsuyui", "classic-repo", {"README.md": "ok\n"})
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
        [str(SCRIPT), "cleanup-classic-all", "public"],
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
        }
    ]
