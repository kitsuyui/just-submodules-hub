from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_every_repo_runs_command_for_each_submodule_as_raw_output_by_default(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote_a = create_remote(
        tmp_path,
        "example-owner",
        "every-a",
        {"README.md": "a\n"},
    )
    remote_b = create_remote(
        tmp_path,
        "example-owner",
        "every-b",
        {"README.md": "b\n"},
    )
    path_a = "repo/github.com/example-owner/every-a"
    path_b = "repo/github.com/example-owner/every-b"
    add_submodule(hub_repo, remote_a, path_a)
    add_submodule(hub_repo, remote_b, path_b)

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "every-repo", "ls", "--jobs", "2"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == f"{path_a}:\nREADME.md\n\n{path_b}:\nREADME.md\n"


def test_every_repo_runs_command_for_each_submodule_as_jsonl(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote_a = create_remote(
        tmp_path,
        "example-owner",
        "every-a",
        {"README.md": "a\n"},
    )
    remote_b = create_remote(
        tmp_path,
        "example-owner",
        "every-b",
        {"README.md": "b\n"},
    )
    path_a = "repo/github.com/example-owner/every-a"
    path_b = "repo/github.com/example-owner/every-b"
    add_submodule(hub_repo, remote_a, path_a)
    add_submodule(hub_repo, remote_b, path_b)

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "every-repo", "ls", "--format", "jsonl", "--jobs", "2"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [row["repo"] for row in rows] == [path_a, path_b]
    assert {row["status"] for row in rows} == {"ok"}
    assert {row["exit_code"] for row in rows} == {"0"}
    assert {row["stdout"] for row in rows} == {"README.md"}


def test_every_repo_reports_failed_commands(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "every-fail",
        {"README.md": "a\n"},
    )
    submodule_path = "repo/github.com/example-owner/every-fail"
    add_submodule(hub_repo, remote, submodule_path)

    proc = subprocess.run(
        [str(ACTION_SCRIPT), "every-repo", "false", "--format", "jsonl", "--jobs", "1"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert rows == [
        {
            "exit_code": "1",
            "repo": submodule_path,
            "status": "failed",
            "stderr": "",
            "stdout": "",
        },
    ]


def test_every_repo_can_filter_by_marker_file(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    python_remote = create_remote(
        tmp_path,
        "example-owner",
        "python-lib",
        {"pyproject.toml": "[project]\nname='python-lib'\n"},
    )
    js_remote = create_remote(
        tmp_path,
        "example-owner",
        "js-lib",
        {"package.json": '{"name":"js-lib"}\n'},
    )
    python_path = "repo/github.com/example-owner/python-lib"
    add_submodule(hub_repo, python_remote, python_path)
    add_submodule(hub_repo, js_remote, "repo/github.com/example-owner/js-lib")

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "every-repo",
            "--marker-file",
            "pyproject.toml",
            "pwd",
            "--format",
            "jsonl",
            "--jobs",
            "2",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    rows = [json.loads(line) for line in proc.stdout.splitlines()]
    assert [row["repo"] for row in rows] == [python_path]
    assert rows[0]["status"] == "ok"
