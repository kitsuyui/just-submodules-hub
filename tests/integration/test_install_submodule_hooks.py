from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote, run, write_executable

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_install_submodule_hooks_installs_detected_managers(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    log_path = tmp_path / "hook-tools.log"
    bin_dir = tmp_path / "bin"
    write_executable(
        bin_dir / "lefthook",
        f'#!/bin/sh\nprintf \'lefthook:%s:%s\\n\' "$PWD" "$*" >> {log_path}\n',
    )
    write_executable(
        bin_dir / "pre-commit",
        f'#!/bin/sh\nprintf \'pre-commit:%s:%s\\n\' "$PWD" "$*" >> {log_path}\n',
    )

    lefthook_remote = create_remote(
        tmp_path,
        "example-owner",
        "lefthook-repo",
        {"lefthook.yml": "pre-commit:\n  jobs: []\n"},
    )
    pre_commit_remote = create_remote(
        tmp_path,
        "example-owner",
        "pre-commit-repo",
        {".pre-commit-config.yaml": "repos: []\n"},
    )
    husky_remote = create_remote(
        tmp_path,
        "example-owner",
        "husky-repo",
        {
            ".husky/pre-commit": "npm test\n",
            ".husky/_/husky.sh": "# generated\n",
        },
    )
    noop_remote = create_remote(
        tmp_path,
        "example-owner",
        "noop-repo",
        {"README.md": "no hooks\n"},
    )

    paths = {
        "lefthook": "repo/github.com/example-owner/lefthook-repo",
        "pre-commit": "repo/github.com/example-owner/pre-commit-repo",
        "husky": "repo/github.com/example-owner/husky-repo",
        "noop": "repo/github.com/example-owner/noop-repo",
    }
    add_submodule(hub_repo, lefthook_remote, paths["lefthook"])
    add_submodule(hub_repo, pre_commit_remote, paths["pre-commit"])
    add_submodule(hub_repo, husky_remote, paths["husky"])
    add_submodule(hub_repo, noop_remote, paths["noop"])

    env = {**os.environ, "PATH": f"{bin_dir}{os.pathsep}{os.environ['PATH']}"}
    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "install-submodule-hooks",
            "--format",
            "jsonl",
            "--jobs",
            "2",
        ],
        cwd=str(hub_repo),
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    by_repo = {row["repo"]: row for row in rows}
    assert by_repo[paths["lefthook"]]["status"] == "installed"
    assert by_repo[paths["lefthook"]]["manager"] == "lefthook"
    assert by_repo[paths["pre-commit"]]["status"] == "installed"
    assert by_repo[paths["pre-commit"]]["manager"] == "pre-commit"
    assert by_repo[paths["husky"]]["status"] == "installed"
    assert by_repo[paths["husky"]]["command"] == "git config core.hooksPath .husky/_"
    assert by_repo[paths["noop"]]["status"] == "noop"
    assert by_repo[paths["noop"]]["manager"] == "no-config"

    log = log_path.read_text(encoding="utf-8")
    assert f"lefthook:{hub_repo / paths['lefthook']}:install" in log
    assert f"pre-commit:{hub_repo / paths['pre-commit']}:install" in log
    assert (
        run(["git", "config", "--get", "core.hooksPath"], cwd=hub_repo / paths["husky"])
        == ".husky/_"
    )


def test_install_submodule_hooks_fails_on_ambiguous_managers(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "ambiguous-repo",
        {
            "lefthook.yml": "pre-commit:\n  jobs: []\n",
            ".pre-commit-config.yaml": "repos: []\n",
        },
    )
    submodule_path = "repo/github.com/example-owner/ambiguous-repo"
    add_submodule(hub_repo, remote, submodule_path)

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "install-submodule-hooks",
            "--format",
            "jsonl",
            "--jobs",
            "1",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert rows == [
        {
            "command": "",
            "exit_code": "1",
            "manager": "ambiguous:lefthook,pre-commit",
            "repo": submodule_path,
            "status": "failed",
            "stderr": "",
            "stdout": "",
        },
    ]


def test_install_submodule_hooks_supports_dry_run(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "dry-run-repo",
        {"lefthook.yml": "pre-commit:\n  jobs: []\n"},
    )
    submodule_path = "repo/github.com/example-owner/dry-run-repo"
    add_submodule(hub_repo, remote, submodule_path)

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "install-submodule-hooks",
            "--format",
            "jsonl",
            "--jobs",
            "1",
            "--dry-run",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert rows[0]["repo"] == submodule_path
    assert rows[0]["status"] == "would-install"
    assert rows[0]["manager"] == "lefthook"
