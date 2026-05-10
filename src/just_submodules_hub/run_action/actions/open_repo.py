from __future__ import annotations

import sys
from pathlib import Path

from just_submodules_hub.openers import open_repo_in_tool
from just_submodules_hub.run_action.registry import action


@action("open-repo")
def open_repo(args: list[str]) -> int:
    if len(args) < 2 or not args[0] or not args[1]:
        print("TOOL and REPO are required", file=sys.stderr)
        return 2
    tool = args[0]
    repo = args[1]
    try:
        open_repo_in_tool(tool=tool, repo=repo, hub_root=Path.cwd())
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0
