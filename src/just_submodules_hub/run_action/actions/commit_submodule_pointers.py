"""Action handler: commit changed submodule pointer updates."""

from __future__ import annotations

import subprocess

from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.run_action.registry import action


def _submodule_pointer_changed(repo_path: str) -> bool:
    """Return True when the submodule HEAD differs from the index entry.

    Mirrors the shell ``submodule_pointer_changed`` function.
    Uses ``git ls-files -s`` for the index OID and ``git -C <path> rev-parse HEAD``
    for the worktree OID, comparing without resolving ``ignore`` settings.
    """
    index_proc = subprocess.run(
        ["git", "ls-files", "-s", "--", repo_path],
        capture_output=True,
        text=True,
        check=False,
    )
    if index_proc.returncode != 0 or not index_proc.stdout.strip():
        return False
    # Output format per line: "<mode> <object> <stage>\t<path>"
    # During a merge conflict, stages 1 (ancestor), 2 (ours), 3 (theirs) are listed
    # instead of stage 0. Only stage 0 is the clean index entry; no stage 0 means
    # the path is unresolved, so treat it as unchanged to avoid a false positive.
    index_oid = None
    for line in index_proc.stdout.splitlines():
        tab_idx = line.find("\t")
        if tab_idx == -1:
            continue
        fields = line[:tab_idx].split()
        if len(fields) >= 3 and fields[2] == "0":
            index_oid = fields[1]
            break
    if index_oid is None:
        return False

    worktree_proc = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    if worktree_proc.returncode != 0 or not worktree_proc.stdout.strip():
        return False
    worktree_oid = worktree_proc.stdout.strip()

    return index_oid != worktree_oid


@action("commit-submodule-pointers")
def commit_submodule_pointers(args: list[str]) -> int:
    """Stage and commit all submodule pointer changes with an optional message."""
    message = args[0] if args else "Update submodule pointers"

    paths = read_gitmodules_paths()
    changed: list[str] = [p for p in paths if p and _submodule_pointer_changed(p)]

    if not changed:
        print("No submodule pointer changes to commit")
        return 0

    add_proc = subprocess.run(
        ["git", "add", "--", *changed],
        check=False,
    )
    if add_proc.returncode != 0:
        return add_proc.returncode

    # Check if there is actually something staged (handles ignore=all case)
    diff_proc = subprocess.run(
        ["git", "diff", "--cached", "--ignore-submodules=none", "--quiet"],
        check=False,
    )
    if diff_proc.returncode == 0:
        print("No staged changes after selecting submodule pointers")
        return 0

    commit_proc = subprocess.run(
        ["git", "commit", "-m", message],
        check=False,
    )
    return commit_proc.returncode
