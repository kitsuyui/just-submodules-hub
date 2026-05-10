from __future__ import annotations

import shutil
import subprocess
import sys

from just_submodules_hub.run_action.registry import action, dispatch


def _create_repo(args: list[str], visibility: str) -> int:
    """Common implementation for create-public-repo and create-private-repo."""
    repo = args[0] if args else ""
    if not repo:
        print("REPO is required", file=sys.stderr)
        return 2

    # Check whether gh is available
    if shutil.which("gh") is None:
        print("gh command not found", file=sys.stderr)
        return 1

    # Check if repo already exists
    check_proc = subprocess.run(
        ["gh", "repo", "view", repo],
        capture_output=True,
        check=False,
    )
    if check_proc.returncode == 0:
        print(f"Repository {repo} already exists. Skipping creation.")
    else:
        create_proc = subprocess.run(
            ["gh", "repo", "create", repo, f"--{visibility}", "--add-readme"],
            check=False,
        )
        if create_proc.returncode != 0:
            return create_proc.returncode

    # Delegate to add-repo via registry dispatch (Python-to-Python, no shell round-trip)
    return dispatch("add-repo", [f"https://github.com/{repo}"])


@action("create-public-repo")
def create_public_repo(args: list[str]) -> int:
    return _create_repo(args, "public")


@action("create-private-repo")
def create_private_repo(args: list[str]) -> int:
    return _create_repo(args, "private")
