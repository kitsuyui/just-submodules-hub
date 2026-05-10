from __future__ import annotations

import just_submodules_hub.linked_worktree_inventory as linked_worktrees


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
