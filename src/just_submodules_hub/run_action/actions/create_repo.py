"""Action handlers for creating a new GitHub repository."""

from __future__ import annotations

import shutil
import subprocess
import sys

from just_submodules_hub.run_action.registry import action


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

    # The calling Just recipe runs add-repo as a second hook-wrapped action.
    # Keeping the two actions separate ensures consumer before/after-add-repo
    # hooks apply identity and local submodule policy to the new checkout.
    return 0


@action("create-public-repo")
def create_public_repo(args: list[str]) -> int:
    """Create a new public GitHub repository."""
    return _create_repo(args, "public")


@action("create-private-repo")
def create_private_repo(args: list[str]) -> int:
    """Create a new private GitHub repository."""
    return _create_repo(args, "private")
