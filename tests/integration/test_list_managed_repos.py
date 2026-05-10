from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import write_executable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def write_gitmodules(hub_repo: Path) -> None:
    (hub_repo / ".gitmodules").write_text(
        """[submodule "repo/github.com/kitsuyui/public-repo"]
\tpath = repo/github.com/kitsuyui/public-repo
\turl = git@github.com:kitsuyui/public-repo.git
[submodule "repo/github.com/kitsuyui/private-repo"]
\tpath = repo/github.com/kitsuyui/private-repo
\turl = git@github.com:kitsuyui/private-repo.git
[submodule "repo/github.com/gitignore-in/tool"]
\tpath = repo/github.com/gitignore-in/tool
\turl = git@github.com:gitignore-in/tool.git
""",
        encoding="utf-8",
    )


def run_action(
    hub_repo: Path, args: list[str], env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(ACTION_SCRIPT), *args],
        cwd=str(hub_repo),
        env={**os.environ, **dict(env or {})},
        text=True,
        capture_output=True,
        check=False,
    )


def test_list_managed_repos_without_filter_preserves_existing_output(
    hub_repo: Path,
) -> None:
    write_gitmodules(hub_repo)

    proc = run_action(hub_repo, ["list-managed-repos"])

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "gitignore-in/tool",
        "kitsuyui/private-repo",
        "kitsuyui/public-repo",
    ]


def test_list_managed_repos_filters_by_owner_without_github_lookup(
    hub_repo: Path,
) -> None:
    write_gitmodules(hub_repo)

    proc = run_action(hub_repo, ["list-managed-repos", "kitsuyui", "all"])

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "kitsuyui/private-repo",
        "kitsuyui/public-repo",
    ]


def test_list_managed_repos_filters_by_github_visibility(
    tmp_path: Path, hub_repo: Path
) -> None:
    write_gitmodules(hub_repo)
    bin_dir = tmp_path / "bin"
    # Fake `gh` that responds to the exact CLI args the Python action will call.
    # The Python implementation calls `gh repo list <owner> --visibility <vis> ...`
    # directly instead of going through `just github repos list`.
    write_executable(
        bin_dir / "gh",
        """#!/bin/sh
if [ "$1" = "repo" ] && [ "$2" = "list" ] && [ "$3" = "kitsuyui" ]; then
  printf '%s\n' 'kitsuyui/private-repo\thttps://github.com/kitsuyui/private-repo'
  printf '%s\n' 'kitsuyui/unmanaged-private\thttps://github.com/kitsuyui/unmanaged-private'
  exit 0
fi
exit 64
""",
    )

    proc = run_action(
        hub_repo,
        ["list-managed-repos", "kitsuyui", "private"],
        env={"PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"},
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["kitsuyui/private-repo"]
