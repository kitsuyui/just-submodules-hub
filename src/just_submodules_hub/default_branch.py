"""Helpers for resolving the default branch of a repository."""

from __future__ import annotations

from contextlib import suppress
from pathlib import Path

from .shell import run


def parse_head_branch_line(remote_show_output: str) -> str | None:
    """Return the branch name from `git remote show` output, or None."""
    for line in remote_show_output.splitlines():
        if "HEAD branch:" in line:
            return line.split("HEAD branch:", 1)[1].strip()
    return None


def resolve_default_branch(
    repo: Path | str,
    *,
    remote: str = "origin",
    fallback: str | None = "main",
) -> str:
    """Resolve a repository's default branch.

    Resolution order:
    1. ``git symbolic-ref --short refs/remotes/<remote>/HEAD``
    2. ``git remote show <remote>`` (parses "HEAD branch:" line)
    3. *fallback* - returned as-is when not None, otherwise RuntimeError is raised.
    """
    cwd = Path(repo)
    with suppress(Exception):
        out = run(
            ["git", "symbolic-ref", "--short", f"refs/remotes/{remote}/HEAD"],
            cwd=cwd,
        )
        prefix = f"{remote}/"
        if out.startswith(prefix):
            return out[len(prefix) :]
        if out:
            return out

    with suppress(Exception):
        show = run(["git", "remote", "show", remote], cwd=cwd)
        parsed = parse_head_branch_line(show)
        if parsed is not None:
            return parsed

    if fallback is not None:
        return fallback
    raise RuntimeError(f"Could not resolve default branch for {repo}")
