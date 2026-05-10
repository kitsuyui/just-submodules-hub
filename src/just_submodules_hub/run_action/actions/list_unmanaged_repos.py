from __future__ import annotations

import sys
from pathlib import Path

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


@action("list-unmanaged-repos")
def list_unmanaged_repos(args: list[str]) -> int:
    if len(args) < 2 or not args[0] or not args[1]:
        print("OWNERS and VISIBILITY are required", file=sys.stderr)
        return 2
    owners_str = args[0]
    visibility = args[1]

    rc = _validate_visibility(visibility)
    if rc != 0:
        return rc

    import just_submodules_hub.run_action.actions.list_github_repos as _lgh  # noqa: PLC0415

    owners = [o for o in owners_str.replace(",", " ").split() if o]
    github_lines: list[str] = []
    for owner in owners:
        try:
            lines = _lgh._list_repos_for_owner(owner, visibility)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        github_lines.extend(lines)

    github_names = sorted({line.split("\t")[0] for line in github_lines if line})

    cwd = Path.cwd()
    paths = read_gitmodules_paths(cwd)
    managed = set(managed_repo_slugs(paths))

    for name in github_names:
        if name not in managed:
            print(name)
    return 0
