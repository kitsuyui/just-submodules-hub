from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/github/list-ready-prs.sh"


def test_list_ready_prs_only_queries_managed_repositories_with_open_prs(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    for repo in ("has-open-pr", "without-open-pr"):
        remote = create_remote(
            tmp_path,
            "kitsuyui",
            repo,
            {"README.md": f"# {repo}\n"},
        )
        add_submodule(hub_repo, remote, f"repo/github.com/kitsuyui/{repo}")

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
  {"repository": {"nameWithOwner": "kitsuyui/has-open-pr"}, "author": {"login": "kitsuyui"}, "url": "https://example.com/pr/1"},
  {"repository": {"nameWithOwner": "kitsuyui/unmanaged"}, "author": {"login": "kitsuyui"}, "url": "https://example.com/pr/2"}
]
EOF
  exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "list" ]; then
  case " $* " in
    *" --repo kitsuyui/has-open-pr "*)
      cat <<'EOF'
[
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "CLEAN",
    "mergeable": "MERGEABLE",
    "statusCheckRollup": [{"name": "test", "conclusion": "SUCCESS"}],
    "url": "https://example.com/pr/1"
  }
]
EOF
      exit 0
      ;;
  esac
fi
echo "unexpected gh invocation: $*" >&2
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT)],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "repo\tauthor\tmerge_state\turl",
        "kitsuyui/has-open-pr\tkitsuyui\tCLEAN\thttps://example.com/pr/1",
    ]


def test_list_ready_prs_queries_candidate_repositories_concurrently(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    for repo in ("first", "second"):
        remote = create_remote(
            tmp_path,
            "kitsuyui",
            repo,
            {"README.md": f"# {repo}\n"},
        )
        add_submodule(hub_repo, remote, f"repo/github.com/kitsuyui/{repo}")

    rendezvous = tmp_path / "rendezvous"
    rendezvous.mkdir()
    fake_bin = tmp_path / "fake-bin"
    fake_gh = fake_bin / "gh"
    write_executable(
        fake_gh,
        f"""#!/bin/sh
set -eu
if [ "$1" = "auth" ] && [ "$2" = "status" ]; then
  exit 0
fi
if [ "$1" = "search" ] && [ "$2" = "prs" ]; then
  cat <<'EOF'
[
  {{"repository": {{"nameWithOwner": "kitsuyui/first"}}, "author": {{"login": "kitsuyui"}}, "url": "https://example.com/pr/1"}},
  {{"repository": {{"nameWithOwner": "kitsuyui/second"}}, "author": {{"login": "kitsuyui"}}, "url": "https://example.com/pr/2"}}
]
EOF
  exit 0
fi
if [ "$1" = "pr" ] && [ "$2" = "list" ]; then
  repo=''
  while [ "$#" -gt 0 ]; do
    if [ "$1" = "--repo" ]; then
      repo=$2
      break
    fi
    shift
  done
  name=${{repo##*/}}
  other=first
  [ "$name" = first ] && other=second
  : > "{rendezvous}/$name"
  attempts=0
  while [ ! -f "{rendezvous}/$other" ]; do
    attempts=$((attempts + 1))
    [ "$attempts" -lt 100 ] || exit 2
    sleep 0.01
  done
  printf '[]\n'
  exit 0
fi
exit 1
""",
    )

    proc = subprocess.run(
        [str(SCRIPT)],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}:{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == "repo\tauthor\tmerge_state\turl\n"
