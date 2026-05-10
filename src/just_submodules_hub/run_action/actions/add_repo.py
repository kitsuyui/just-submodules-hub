"""Action handler: add a GitHub repository as a submodule."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from just_submodules_hub.repo_paths import _strip_repo_transport
from just_submodules_hub.run_action.actions._helpers import set_submodule_ignore_value
from just_submodules_hub.run_action.registry import action

_GITHUB_COM_PREFIX = "repo/github.com/"


def _url_to_repo_dir(repo_url_input: str) -> str:
    r"""Convert a GitHub URL / slug to the local submodule directory path.

    Mirrors the shell logic::

        repo_path=$(echo "$repo_url_input" | sed -E 's#^(git@github.com:|https://github.com/)##; s#\\.git$##')
        repo_dir="repo/github.com/${repo_path}"

    Examples::

        https://github.com/owner/name  ->  repo/github.com/owner/name
        git@github.com:owner/name.git  ->  repo/github.com/owner/name
        owner/name                     ->  repo/github.com/owner/name
    """
    slug = _strip_repo_transport(repo_url_input)
    # _strip_repo_transport handles git@/https:// prefixes and .git suffix.
    # If the slug already contains the full path prefix, keep it as-is.
    if slug.startswith(_GITHUB_COM_PREFIX):
        return slug
    return f"{_GITHUB_COM_PREFIX}{slug}"


@action("add-repo")
def add_repo(args: list[str]) -> int:
    """Register a GitHub repository as a shallow submodule with ``ignore = all``."""
    repo_url_input = args[0] if args else ""
    if not repo_url_input:
        print("REPO_URL is required", file=sys.stderr)
        return 2

    try:
        repo_dir = _url_to_repo_dir(repo_url_input)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    # Reconstruct the canonical SSH URL from the slug
    # e.g. repo/github.com/owner/name  ->  git@github.com:owner/name.git
    slug = repo_dir.removeprefix(_GITHUB_COM_PREFIX)
    repo_url = f"git@github.com:{slug}.git"

    # Clean up leftovers from a previously failed add (only under .git/modules)
    modules_dir = Path(".git") / "modules" / repo_dir
    if modules_dir.is_dir() and not Path(repo_dir).is_dir():
        shutil.rmtree(modules_dir)

    proc = subprocess.run(
        ["git", "submodule", "add", "--", repo_url, repo_dir],
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode

    proc = subprocess.run(
        [
            "git",
            "config",
            "-f",
            ".gitmodules",
            f"submodule.{repo_dir}.shallow",
            "true",
        ],
        check=False,
    )
    if proc.returncode != 0:
        return proc.returncode

    return set_submodule_ignore_value(repo_dir, "all")
