from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from just_submodules_hub.run_action.registry import action

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "run_submodule_command.py"


@action("every-repo")
def every_repo(args: list[str]) -> int:
    if not args:
        print("COMMAND is required", file=sys.stderr)
        return 2

    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        str(_SCRIPT),
    ] + args
    proc = subprocess.run(cmd, check=False)
    return proc.returncode
