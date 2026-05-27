from __future__ import annotations

import os
import subprocess
from pathlib import Path

from .helpers import (
    add_submodule,
    advance_remote,
    create_remote,
    git_head,
    run,
    write_executable,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ACTION_SCRIPT = PROJECT_ROOT / "scripts/repo/run-action.sh"


def test_reconcile_submodule_worktree_pulls_default_branch(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "default-pull",
        {"README.md": "before\n"},
    )
    submodule_path = "repo/github.com/example-owner/default-pull"
    add_submodule(hub_repo, remote, submodule_path)
    expected = advance_remote(remote, "README.md", "after\n", "Update remote")

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "reconcile-submodule-worktree",
            submodule_path,
            "--format",
            "tsv",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert git_head(hub_repo / submodule_path) == expected
    assert (
        f"{submodule_path}\tupdated\tpull-default\tmain\t\tclean\tfast-forwarded"
        in proc.stdout.splitlines()
    )


def test_reconcile_submodule_worktree_settles_merged_pr_branch(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "merged-pr",
        {"README.md": "before\n"},
    )
    submodule_path = "repo/github.com/example-owner/merged-pr"
    add_submodule(hub_repo, remote, submodule_path)
    submodule = hub_repo / submodule_path
    run(["git", "switch", "-c", "feature/merged"], cwd=submodule)

    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "gh",
        """#!/bin/sh
printf '%s\n' '{"number":123,"state":"MERGED","mergedAt":"2026-04-26T00:00:00Z"}'
""",
    )

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "reconcile-submodule-worktree",
            submodule_path,
            "--format",
            "tsv",
        ],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert run(["git", "branch", "--show-current"], cwd=submodule) == "main"
    assert (
        f"{submodule_path}\tsettled\tswitch-default\tmain\t123\tclean"
        "\tpr merged; switched to default branch" in proc.stdout.splitlines()
    )


def test_reconcile_submodule_worktrees_aggregates_jsonl(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    remote = create_remote(
        tmp_path,
        "example-owner",
        "all-default",
        {"README.md": "before\n"},
    )
    submodule_path = "repo/github.com/example-owner/all-default"
    add_submodule(hub_repo, remote, submodule_path)

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "reconcile-submodule-worktrees",
            "--format",
            "jsonl",
            "--no-prefilter",
        ],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert f'"repo": "{submodule_path}"' in proc.stdout
    assert '"action": "pull-default"' in proc.stdout


def test_reconcile_submodule_worktree_pr_none_pull_failure_returns_failed(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    """Pull failure with no PR (state=none) must exit 1, not 0."""
    remote = create_remote(
        tmp_path,
        "example-owner",
        "pr-none-fail",
        {"README.md": "initial\n"},
    )
    submodule_path = "repo/github.com/example-owner/pr-none-fail"
    add_submodule(hub_repo, remote, submodule_path)
    submodule = hub_repo / submodule_path
    # Create a local-only topic branch with no upstream tracking
    run(["git", "switch", "-c", "topic/no-remote"], cwd=submodule)

    fake_bin = tmp_path / "bin-none"
    fake_bin.mkdir()
    # gh returns "no pull requests found" → state=none
    write_executable(
        fake_bin / "gh",
        '#!/bin/sh\necho "no pull requests found" >&2\nexit 1\n',
    )

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "reconcile-submodule-worktree",
            submodule_path,
            "--format",
            "tsv",
        ],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1, (
        "expected exit 1 when pull fails with no PR, got 0\n" + proc.stdout
    )
    assert "failed" in proc.stdout
    assert "pr-none" in proc.stdout


def test_reconcile_submodule_worktree_pr_unknown_pull_failure_returns_failed(
    tmp_path: Path,
    hub_repo: Path,
) -> None:
    """Pull failure with gh error (state=unknown) must exit 1, not 0."""
    remote = create_remote(
        tmp_path,
        "example-owner",
        "pr-unknown-fail",
        {"README.md": "initial\n"},
    )
    submodule_path = "repo/github.com/example-owner/pr-unknown-fail"
    add_submodule(hub_repo, remote, submodule_path)
    submodule = hub_repo / submodule_path
    # Create a local-only topic branch with no upstream tracking
    run(["git", "switch", "-c", "topic/gh-error"], cwd=submodule)

    fake_bin = tmp_path / "bin-unknown"
    fake_bin.mkdir()
    # gh exits non-zero with an unrecognized error → state=unknown
    write_executable(
        fake_bin / "gh",
        '#!/bin/sh\necho "API rate limit exceeded" >&2\nexit 1\n',
    )

    proc = subprocess.run(
        [
            str(ACTION_SCRIPT),
            "reconcile-submodule-worktree",
            submodule_path,
            "--format",
            "tsv",
        ],
        cwd=str(hub_repo),
        env={**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 1, (
        "expected exit 1 when pull fails with unknown PR state, got 0\n" + proc.stdout
    )
    assert "failed" in proc.stdout
    assert "pr-unknown" in proc.stdout
