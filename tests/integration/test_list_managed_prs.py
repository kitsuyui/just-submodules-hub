from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/github/list-managed-prs.sh"


def test_list_managed_prs_filters_to_managed_repositories(tmp_path: Path, hub_repo: Path) -> None:
    managed_remote = create_remote(
        tmp_path,
        "kitsuyui",
        "ts-playground",
        {"package.json": '{"name":"ts-playground"}\n'},
    )
    add_submodule(hub_repo, managed_remote, "repo/github.com/kitsuyui/ts-playground")

    fake_bin = tmp_path / "fake-bin"
    fake_gh = fake_bin / "gh"
    write_executable(
        fake_gh,
        """#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "search" ] && [ "$2" = "prs" ]; then
  cat <<'EOF'
[
  {
    "repository": {"nameWithOwner": "kitsuyui/ts-playground"},
    "author": {"login": "kitsuyui"},
    "url": "https://example.com/pr/1"
  },
  {
    "repository": {"nameWithOwner": "kitsuyui/unmanaged"},
    "author": {"login": "kitsuyui"},
    "url": "https://example.com/pr/2"
  }
]
EOF
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT), "open"],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "repo\tauthor\turl",
        "kitsuyui/ts-playground\tkitsuyui\thttps://example.com/pr/1",
    ]
