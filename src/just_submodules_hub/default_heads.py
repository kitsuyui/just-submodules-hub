"""Bulk fetching of remote default-branch/OID pairs via GitHub GraphQL."""

from __future__ import annotations

import contextlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from tqdm import tqdm

from .github_cli import GH_COMMAND_TIMEOUT_SECONDS
from .repo_paths import repo_display_name, repo_owner
from .shell import run
from .submodule_batch import tick

GRAPHQL_QUERY = """
query($owner: String!, $cursor: String) {
  repositoryOwner(login: $owner) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
      nodes {
        name
        defaultBranchRef {
          name
          target {
            ... on Commit {
              oid
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""


@dataclass(frozen=True)
class DefaultHead:
    """Remote default branch and its HEAD commit OID."""

    branch: str
    oid: str


def gh_graphql(owner: str, cursor: str | None) -> dict:
    """Execute the GRAPHQL_QUERY for *owner* and return the parsed JSON response."""
    cmd = [
        "gh",
        "api",
        "graphql",
        "-F",
        f"owner={owner}",
        "-f",
        f"query={GRAPHQL_QUERY}",
    ]
    if cursor:
        cmd.extend(["-F", f"cursor={cursor}"])
    out = run(cmd, timeout=GH_COMMAND_TIMEOUT_SECONDS)
    return cast(dict[Any, Any], json.loads(out))


def extract_default_head(node: dict, owner: str) -> tuple[str, DefaultHead] | None:
    """Extract a (slug, DefaultHead) pair from a GraphQL repository node.

    Returns None when the node lacks a valid defaultBranchRef or OID.
    """
    default_ref = node.get("defaultBranchRef")
    if not default_ref:
        return None
    target = default_ref.get("target") or {}
    oid = target.get("oid")
    name = default_ref.get("name")
    repo_name = node.get("name")
    if not oid or not name or not repo_name:
        return None
    return f"{owner}/{repo_name}", DefaultHead(name, oid)


def fetch_owner_default_heads(
    owner: str,
    bar: tqdm[Any] | None,
) -> dict[str, DefaultHead]:
    """Fetch all default-branch HEAD OIDs for every repository owned by *owner*."""
    cursor: str | None = None
    found: dict[str, DefaultHead] = {}

    while True:
        payload = gh_graphql(owner, cursor)
        tick(bar)

        repo_owner_payload = payload.get("data", {}).get("repositoryOwner")
        if repo_owner_payload is None:
            raise RuntimeError(f"repository owner not found: {owner}")

        repos = repo_owner_payload["repositories"]
        for node in repos.get("nodes", []):
            extracted = extract_default_head(node, owner)
            if extracted is None:
                continue
            slug, head = extracted
            found[slug] = head

        page_info = repos.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")
        if not cursor:
            break
        if bar is not None:
            bar.total = (bar.total or 0) + 1
            bar.refresh()

    return found


def owner_prefilter_total(paths: Iterable[str], prefilter: bool) -> int:
    """Return the number of extra progress-bar ticks needed for the prefilter phase."""
    if not prefilter:
        return 0
    return len({repo_owner(path) for path in paths})


def fetch_default_heads_for_paths(
    paths: Iterable[str],
    bar: tqdm[Any] | None,
) -> dict[str, DefaultHead]:
    """Fetch default-branch HEAD OIDs for every owner found in *paths*."""
    path_list = list(paths)
    owners = sorted({repo_owner(path) for path in path_list})
    heads: dict[str, DefaultHead] = {}

    for owner in owners:
        heads.update(fetch_owner_default_heads(owner, bar))

    return heads


def local_head(repo_path: str | Path) -> tuple[str, str]:
    """Return the local (branch, OID) pair for *repo_path*.

    Returns ("DETACHED", <oid>) when HEAD is in detached state.
    Returns ("DETACHED", "") when *repo_path* has no Git repository
    (e.g., a submodule directory that has not been initialized yet).
    """
    cwd = Path(repo_path)
    branch = "DETACHED"
    oid = ""
    with contextlib.suppress(Exception):
        branch = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd)
    with contextlib.suppress(Exception):
        oid = run(["git", "rev-parse", "HEAD"], cwd=cwd)
    return branch, oid


def matching_default_head(
    repo_path: str,
    remote_heads: dict[str, DefaultHead],
) -> DefaultHead | None:
    """Return the remote DefaultHead when the local repo is already up to date.

    Returns None when *repo_path* is not in *remote_heads* or when the local
    branch / OID differ from the remote default.
    """
    remote = remote_heads.get(repo_display_name(repo_path))
    if remote is None:
        return None
    local_branch, local_oid = local_head(repo_path)
    if local_branch == remote.branch and local_oid == remote.oid:
        return remote
    return None
