"""Action handler: list repositories that are both managed and on GitHub."""

from __future__ import annotations

import sys
from pathlib import Path

import just_submodules_hub.run_action.actions.list_github_repos as list_github_repos_module  # noqa: E501
from just_submodules_hub.gitmodules import managed_repo_slugs, read_gitmodules_paths
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


def _get_managed_slugs(cwd: Path) -> list[str]:
    paths = read_gitmodules_paths(cwd)
    return managed_repo_slugs(paths)


def _filter_by_owners(slugs: list[str], owners_str: str) -> list[str]:
    allowed = {o for o in owners_str.replace(",", " ").split() if o}
    return [slug for slug in slugs if slug.split("/")[0] in allowed]


@action("list-managed-repos")
def list_managed_repos(args: list[str]) -> int:
    """List managed repositories, optionally filtered by owner and visibility."""
    owners_str = args[0] if args else ""
    visibility = args[1] if len(args) > 1 else "all"

    rc = _validate_visibility(visibility)
    if rc != 0:
        return rc

    cwd = Path.cwd()

    if visibility == "all":
        slugs = _get_managed_slugs(cwd)
        if owners_str:
            slugs = _filter_by_owners(slugs, owners_str)
        for slug in slugs:
            print(slug)
        return 0

    # visibility != "all": need OWNERS to filter via GitHub
    if not owners_str:
        print("OWNERS is required when VISIBILITY is not all", file=sys.stderr)
        return 2

    # Call list-github-repos via the Python entrypoint to avoid shell dependency
    github_lines: list[str] = []
    owners = [o for o in owners_str.replace(",", " ").split() if o]
    for owner in owners:
        try:
            lines = list_github_repos_module._list_repos_for_owner(owner, visibility)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        github_lines.extend(lines)

    github_names = sorted({line.split("\t")[0] for line in github_lines if line})
    managed = sorted(_get_managed_slugs(cwd))

    github_set = set(github_names)
    result = [slug for slug in managed if slug in github_set]
    for slug in result:
        print(slug)
    return 0
