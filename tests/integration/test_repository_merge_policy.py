from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, init_hub, write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/github/repository-merge-policy.sh"


def test_repository_merge_policy_status_reports_current_methods(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/example" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":false}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "status", "squash", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload == {
        "repo": "kitsuyui/example",
        "visibility": "public",
        "method": "squash",
        "allowed": True,
    }


def test_repository_merge_policy_disable_updates_one_method(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    payload_capture = tmp_path / "payload.json"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/example" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":true}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PATCH" ] && [ "$4" = "repos/kitsuyui/example" ] && [ "$5" = "--input" ] && [ "$6" = "-" ]; then
  cat > "{payload_capture}"
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "disable", "squash", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    posted_payload = json.loads(payload_capture.read_text(encoding="utf-8"))
    assert posted_payload == {"allow_squash_merge": False}
    payload = json.loads(proc.stdout)
    assert payload["action"] == "disabled"
    assert payload["method"] == "squash"
    assert payload["before"]["allowed"] is True
    assert payload["after"]["allowed"] is False


def test_repository_merge_policy_enable_updates_one_method(tmp_path: Path) -> None:
    fake_bin = tmp_path / "fake-bin"
    payload_capture = tmp_path / "payload.json"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/example" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PATCH" ] && [ "$4" = "repos/kitsuyui/example" ] && [ "$5" = "--input" ] && [ "$6" = "-" ]; then
  cat > "{payload_capture}"
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/example","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":true}}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "enable", "rebase", "kitsuyui/example"],
        cwd=str(tmp_path),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    posted_payload = json.loads(payload_capture.read_text(encoding="utf-8"))
    assert posted_payload == {"allow_rebase_merge": True}
    payload = json.loads(proc.stdout)
    assert payload["action"] == "enabled"
    assert payload["method"] == "rebase"
    assert payload["before"]["allowed"] is False
    assert payload["after"]["allowed"] is True


def test_repository_merge_policy_status_all_filters_managed_repositories(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)

    public_remote = create_remote(tmp_path, "kitsuyui", "public-repo", {"README.md": "ok\n"})
    private_remote = create_remote(tmp_path, "kitsuyui", "private-repo", {"README.md": "ok\n"})
    wiki_remote = create_remote(tmp_path, "kitsuyui", "public-repo.wiki", {"Home.md": "ok\n"})
    add_submodule(hub_repo, public_remote, "repo/github.com/kitsuyui/public-repo")
    add_submodule(hub_repo, private_remote, "repo/github.com/kitsuyui/private-repo")
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
{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/private-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/private-repo","visibility":"PRIVATE","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":true}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo.wiki" ]; then
  echo "wiki repo should have been skipped" >&2
  exit 1
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "status-all", "squash", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["action"] == "status-all"
    assert payload["method"] == "squash"
    assert payload["visibility"] == "public"
    assert [item["repo"] for item in payload["repos"]] == ["kitsuyui/public-repo"]
    assert payload["repos"][0]["allowed"] is False
    assert "squash status-all" in proc.stderr


def test_repository_merge_policy_disable_all_updates_filtered_repositories(tmp_path: Path) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)

    public_remote = create_remote(tmp_path, "kitsuyui", "public-repo", {"README.md": "ok\n"})
    private_remote = create_remote(tmp_path, "kitsuyui", "private-repo", {"README.md": "ok\n"})
    add_submodule(hub_repo, public_remote, "repo/github.com/kitsuyui/public-repo")
    add_submodule(hub_repo, private_remote, "repo/github.com/kitsuyui/private-repo")

    fake_bin = tmp_path / "fake-bin"
    calls = tmp_path / "calls.txt"
    write_executable(
        fake_bin / "gh",
        f"""#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":true}}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/private-repo" ]; then
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/private-repo","visibility":"PRIVATE","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":true}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PATCH" ] && [ "$4" = "repos/kitsuyui/public-repo" ] && [ "$5" = "--input" ] && [ "$6" = "-" ]; then
  echo "$4" >> "{calls}"
  cat >/dev/null
  cat <<'EOF'
{{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}}
EOF
  exit 0
fi
if [ "$1" = "api" ] && [ "$2" = "--method" ] && [ "$3" = "PATCH" ] && [ "$4" = "repos/kitsuyui/private-repo" ]; then
  echo "private repo should not have been updated" >&2
  exit 1
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "disable-all", "rebase", "public"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert calls.read_text(encoding="utf-8").splitlines() == ["repos/kitsuyui/public-repo"]
    payload = json.loads(proc.stdout)
    assert payload["action"] == "disable-all"
    assert payload["method"] == "rebase"
    assert payload["visibility"] == "public"
    assert [item["repo"] for item in payload["results"]] == ["kitsuyui/public-repo"]
    assert payload["results"][0]["after"]["allowed"] is False


def test_repository_merge_policy_all_actions_default_to_public(tmp_path: Path) -> None:
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
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/public-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/public-repo","visibility":"PUBLIC","mergeCommitAllowed":true,"squashMergeAllowed":false,"rebaseMergeAllowed":false}
EOF
  exit 0
fi
if [ "$1" = "repo" ] && [ "$2" = "view" ] && [ "$3" = "kitsuyui/private-repo" ]; then
  cat <<'EOF'
{"nameWithOwner":"kitsuyui/private-repo","visibility":"PRIVATE","mergeCommitAllowed":true,"squashMergeAllowed":true,"rebaseMergeAllowed":true}
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "status-all", "squash"],
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
