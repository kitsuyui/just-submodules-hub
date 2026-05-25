"""Action handlers for listing GitHub repositories for an owner or set of owners."""

from __future__ import annotations

import subprocess
import sys

from just_submodules_hub.run_action.registry import action

VALID_VISIBILITIES = frozenset({"public", "private", "internal", "all"})


def _validate_visibility(visibility: str) -> int:
    if visibility not in VALID_VISIBILITIES:
        print(
            f"VISIBILITY must be one of: public/private/internal/all: {visibility}",
            file=sys.stderr,
        )
        return 2
    return 0


def _list_repos_for_owner(owner: str, visibility: str) -> list[str]:
    r"""Call gh repo list and return lines of 'nameWithOwner\turl'."""
    cmd = [
        "gh",
        "repo",
        "list",
        owner,
        "--limit",
        "1000",
        "--json",
        "nameWithOwner,url,isArchived,isFork",
        "--jq",
        '.[] | select((.isArchived | not) and (.isFork | not)) | "\\(.nameWithOwner)\\t\\(.url)"',  # noqa: E501
    ]
    if visibility != "all":
        cmd = [
            "gh",
            "repo",
            "list",
            owner,
            "--visibility",
            visibility,
            "--limit",
            "1000",
            "--json",
            "nameWithOwner,url,isArchived,isFork",
            "--jq",
            '.[] | select((.isArchived | not) and (.isFork | not)) | "\\(.nameWithOwner)\\t\\(.url)"',  # noqa: E501
        ]
    proc = subprocess.run(
        cmd,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        detail = proc.stderr.strip()
        raise RuntimeError(
            f"gh repo list failed [owner={owner!r} visibility={visibility!r}]: {detail}"
        )
    return [line for line in proc.stdout.splitlines() if line]


@action("list-github-repos-owner")
def list_github_repos_owner(args: list[str]) -> int:
    """List GitHub repositories for a single owner with a given visibility filter."""
    if len(args) < 2 or not args[0] or not args[1]:
        print("OWNER and VISIBILITY are required", file=sys.stderr)
        return 2
    owner = args[0]
    visibility = args[1]
    rc = _validate_visibility(visibility)
    if rc != 0:
        return rc
    try:
        lines = _list_repos_for_owner(owner, visibility)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    for line in lines:
        print(line)
    return 0


@action("list-github-repos")
def list_github_repos(args: list[str]) -> int:
    """List GitHub repositories for multiple owners, deduplicating by nameWithOwner."""
    if len(args) < 2 or not args[0] or not args[1]:
        print("OWNERS and VISIBILITY are required", file=sys.stderr)
        return 2
    owners_str = args[0]
    visibility = args[1]
    rc = _validate_visibility(visibility)
    if rc != 0:
        return rc

    owners = [o for o in owners_str.replace(",", " ").split() if o]
    seen: dict[str, bool] = {}
    for owner in owners:
        try:
            lines = _list_repos_for_owner(owner, visibility)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        for line in lines:
            name_with_owner = line.split("\t")[0]
            if name_with_owner not in seen:
                seen[name_with_owner] = True
                print(line)
    return 0
