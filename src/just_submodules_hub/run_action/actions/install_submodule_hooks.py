"""Action handler: install Git hook managers in managed submodules."""

from __future__ import annotations

import subprocess
from pathlib import Path

from just_submodules_hub.run_action.registry import action

_PROJECT_ROOT = Path(__file__).resolve().parents[4]


@action("install-submodule-hooks")
def install_submodule_hooks(args: list[str]) -> int:
    """Install configured Git hook managers in managed submodules."""
    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        "-m",
        "just_submodules_hub.submodule_hooks",
        *args,
    ]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode
