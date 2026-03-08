from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/github/default-branch-ruleset.sh"


def test_default_branch_ruleset_status_reports_missing_rule(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets" ]; then
  echo '[]'
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "status", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["repo"] == "kitsuyui/example"
    assert payload["missing_rule_types"] == ["deletion", "non_fast_forward"]
    assert payload["baseline_compliant"] is False


def test_default_branch_ruleset_apply_updates_existing_managed_ruleset(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    payload_capture = tmp_path / "payload.json"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/example","visibility":"PRIVATE","defaultBranchRef":{{"name":"main"}}}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets" ] && [ "${{3:-}}" != "--input" ]; then
  cat <<'EOF'
[{{"id":42,"name":"default-branch-baseline"}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets/42" ]; then
  cat <<'EOF'
[{{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{{"ref_name":{{"include":["refs/heads/main"],"exclude":[]}}}},"rules":[{{"type":"pull_request","parameters":{{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}}}},{{"type":"non_fast_forward"}},{{"type":"deletion"}}]}}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PUT" ] && [ "$4" = "repos/kitsuyui/example/rulesets/42" ] && [ "$5" = "--input" ]; then
  cp "$6" "{payload_capture}"
  cat <<'EOF'
{{"id":42}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "apply", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["action"] == "updated"
    posted_payload = json.loads(payload_capture.read_text(encoding="utf-8"))
    assert posted_payload["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    assert [rule["type"] for rule in posted_payload["rules"]] == ["pull_request", "non_fast_forward", "deletion"]


def test_default_branch_ruleset_legacy_status_reports_manual_review_for_uncovered_rules(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets" ]; then
  cat <<'EOF'
[{"id":42,"name":"default-branch-baseline"},{"id":43,"name":"protect-main"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets/42" ]; then
  cat <<'EOF'
{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets/43" ]; then
  cat <<'EOF'
{"id":43,"name":"protect-main","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"required_linear_history"}]}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "legacy-status", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["legacy_rulesets"][0]["name"] == "protect-main"
    assert payload["legacy_rulesets"][0]["deletable"] is False
    assert payload["legacy_rulesets"][0]["uncovered_rule_types"] == ["required_linear_history"]


def test_default_branch_ruleset_delete_if_redundant_deletes_safe_legacy_ruleset(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets" ]; then
  cat <<'EOF'
[{"id":42,"name":"default-branch-baseline"},{"id":43,"name":"protect-main"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets/42" ]; then
  cat <<'EOF'
{"id":42,"name":"default-branch-baseline","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rulesets/43" ]; then
  cat <<'EOF'
{"id":43,"name":"protect-main","target":"branch","enforcement":"active","conditions":{"ref_name":{"include":["refs/heads/main"],"exclude":[]}},"rules":[{"type":"deletion"}]}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "DELETE" ] && [ "$4" = "repos/kitsuyui/example/rulesets/43" ]; then
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "delete-if-redundant", "kitsuyui/example", "protect-main"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["action"] == "deleted"
    assert payload["ruleset_name"] == "protect-main"


def test_default_branch_classic_protection_status_reports_redundant_protection(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/branches/main/protection" ]; then
  cat <<'EOF'
{"required_status_checks":null,"enforce_admins":{"enabled":false},"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null,"required_linear_history":{"enabled":false},"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false},"required_conversation_resolution":{"enabled":false},"block_creations":{"enabled":false},"lock_branch":{"enabled":false},"allow_fork_syncing":{"enabled":false}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "classic-status", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["classic_branch_protection_found"] is True
    assert payload["deletable"] is True
    assert payload["uncovered_settings"] == []


def test_default_branch_classic_protection_delete_if_redundant_deletes_safe_protection(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","defaultBranchRef":{"name":"main"}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/rules/branches/main" ]; then
  cat <<'EOF'
[{"type":"pull_request","parameters":{"required_approving_review_count":0,"dismiss_stale_reviews_on_push":false,"require_code_owner_review":false,"require_last_push_approval":false,"required_review_thread_resolution":false}},{"type":"non_fast_forward"},{"type":"deletion"}]
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "repos/kitsuyui/example/branches/main/protection" ]; then
  cat <<'EOF'
{"required_status_checks":null,"enforce_admins":{"enabled":false},"required_pull_request_reviews":{"required_approving_review_count":0},"restrictions":null,"required_linear_history":{"enabled":false},"allow_force_pushes":{"enabled":false},"allow_deletions":{"enabled":false},"required_conversation_resolution":{"enabled":false},"block_creations":{"enabled":false},"lock_branch":{"enabled":false},"allow_fork_syncing":{"enabled":false}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "DELETE" ] && [ "$4" = "repos/kitsuyui/example/branches/main/protection" ]; then
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "classic-delete-if-redundant", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["action"] == "deleted"
    assert payload["deleted"] == "classic_branch_protection"
