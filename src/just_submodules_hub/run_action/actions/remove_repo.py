from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from just_submodules_hub.repo_paths import resolve_repo_input
from just_submodules_hub.run_action.registry import action


@action("remove-repo")
def remove_repo(args: list[str]) -> int:
    repo_input = args[0] if args else ""
    if not repo_input:
        print("REPO is required", file=sys.stderr)
        return 2

    try:
        repo_path = resolve_repo_input(repo_input, Path.cwd())
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 2

    proc = subprocess.run(
        ["git", "submodule", "deinit", "-f", "--", repo_path],
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode

    modules_dir = Path(".git") / "modules" / repo_path
    if modules_dir.exists():
        shutil.rmtree(modules_dir)

    proc = subprocess.run(
        ["git", "rm", "-f", repo_path],
        check=False,
    )
    return proc.returncode
