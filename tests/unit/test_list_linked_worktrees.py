from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/list_linked_worktrees.py"

spec = importlib.util.spec_from_file_location("list_linked_worktrees", SCRIPT_PATH)
assert spec is not None
linked_worktrees = importlib.util.module_from_spec(spec)
sys.modules["list_linked_worktrees"] = linked_worktrees
assert spec.loader is not None
spec.loader.exec_module(linked_worktrees)


def test_parse_porcelain_reports_branch_and_detached_worktrees() -> None:
    records = linked_worktrees.parse_porcelain(
        """worktree /repo
HEAD 1111111111111111111111111111111111111111
branch refs/heads/main

worktree /repo-feature
HEAD 2222222222222222222222222222222222222222
detached

""",
    )

    assert records == [
        linked_worktrees.WorktreeRecord(
            path="/repo",
            head="1111111111111111111111111111111111111111",
            branch="main",
            detached="no",
            locked="no",
            prunable="no",
            message="",
        ),
        linked_worktrees.WorktreeRecord(
            path="/repo-feature",
            head="2222222222222222222222222222222222222222",
            branch="",
            detached="yes",
            locked="no",
            prunable="no",
            message="",
        ),
    ]


def test_parse_porcelain_preserves_lock_and_prune_reasons() -> None:
    records = linked_worktrees.parse_porcelain(
        """worktree /repo-old
HEAD 3333333333333333333333333333333333333333
branch refs/heads/old
locked still in use
prunable gitdir file points to non-existent location
""",
    )

    assert records == [
        linked_worktrees.WorktreeRecord(
            path="/repo-old",
            head="3333333333333333333333333333333333333333",
            branch="old",
            detached="no",
            locked="yes",
            prunable="yes",
            message=(
                "locked: still in use;"
                " prunable: gitdir file points to non-existent location"
            ),
        ),
    ]
