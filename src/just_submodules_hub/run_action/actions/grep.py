from __future__ import annotations

import subprocess

from just_submodules_hub.run_action.registry import action


@action("grep")
def grep(args: list[str]) -> int:
    proc = subprocess.run(
        ["git", "grep", "--recurse-submodules"] + args,
        check=False,
    )
    return proc.returncode
