"""Action handler: run git grep across all submodule repositories."""

from __future__ import annotations

import subprocess

from just_submodules_hub.run_action.registry import action


@action("grep")
def grep(args: list[str]) -> int:
    """Run ``git grep --recurse-submodules`` with the given arguments."""
    proc = subprocess.run(
        ["git", "grep", "--recurse-submodules", *args],
        check=False,
    )
    return proc.returncode
