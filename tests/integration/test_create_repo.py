from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import create_remote, init_hub, run, write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_create_repo_adds_directly_to_hub_and_runs_add_hooks(
    tmp_path: Path,
) -> None:
    hub_repo = tmp_path / "hub"
    init_hub(hub_repo)

    hooks_file = tmp_path / "hooks.txt"
    (hub_repo / "justfile").write_text(
        f'''
import "{PROJECT_ROOT / "just/index.just"}"

before-add-repo REPO:
  @printf 'before=%s\\n' '{{{{REPO}}}}' >> "{hooks_file}"

after-add-repo REPO:
  @printf 'after=%s\\n' '{{{{REPO}}}}' >> "{hooks_file}"
'''.lstrip(),
        encoding="utf-8",
    )

    remote = create_remote(
        tmp_path,
        "example-owner",
        "example-repo",
        {"README.md": "created remotely\n"},
    )
    run(
        [
            "git",
            "config",
            f"url.{remote.as_uri()}.insteadOf",
            "git@github.com:example-owner/example-repo.git",
        ],
        cwd=hub_repo,
    )

    fake_bin = tmp_path / "bin"
    gh_calls = tmp_path / "gh-calls.txt"
    write_executable(
        fake_bin / "gh",
        f'''#!/bin/sh
printf '%s\\n' "$*" >> "{gh_calls}"
case "$1 $2" in
  "repo view") exit 1 ;;
  "repo create") exit 0 ;;
esac
exit 2
''',
    )

    env = {
        **os.environ,
        "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}",
        "GIT_ALLOW_PROTOCOL": "file",
    }
    proc = subprocess.run(
        [
            "just",
            "github::repos::public::create",
            "example-owner/example-repo",
        ],
        cwd=hub_repo,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert gh_calls.read_text(encoding="utf-8").splitlines() == [
        "repo view example-owner/example-repo",
        "repo create example-owner/example-repo --public --add-readme",
    ]
    assert hooks_file.read_text(encoding="utf-8").splitlines() == [
        "before=https://github.com/example-owner/example-repo",
        "after=https://github.com/example-owner/example-repo",
    ]
    managed_repo = hub_repo / "repo/github.com/example-owner/example-repo"
    assert run(["git", "rev-parse", "HEAD"], cwd=managed_repo)
    assert (
        run(
            [
                "git",
                "config",
                "-f",
                ".gitmodules",
                "--get",
                "submodule.repo/github.com/example-owner/example-repo.url",
            ],
            cwd=hub_repo,
        )
        == "git@github.com:example-owner/example-repo.git"
    )
    assert not (hub_repo / "example-repo").exists()
