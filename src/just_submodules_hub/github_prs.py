"""GitHub Pull Request search and filtering helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .github_cli import run_gh
from .gitmodules import managed_repo_slugs

VALID_STATES = {"open", "closed", "merged", "all"}


@dataclass(frozen=True)
class PullRequestState:
    """Captured state of a pull request for a worktree branch."""

    number: str
    state: str
    draft: str
    message: str


def _summarize(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout).strip()
    return " ".join(text.split()) or f"exit {proc.returncode}"


def gh_pr_view(repo: Path) -> PullRequestState:
    """Query the current PR state for the checked-out branch in *repo*."""
    if shutil.which("gh") is None:
        return PullRequestState("", "unknown", "", "gh not found")
    proc = run_gh(
        ["pr", "view", "--json", "number,state,isDraft,mergedAt"],
        cwd=repo,
    )
    if proc.returncode != 0:
        message = _summarize(proc)
        lowered = message.lower()
        if "no pull requests found" in lowered or "no pull request" in lowered:
            return PullRequestState("", "none", "", "no pull request metadata")
        return PullRequestState("", "unknown", "", message)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return PullRequestState("", "unknown", "", "gh returned invalid JSON")
    number = str(data.get("number") or "")
    state = str(data.get("state") or "").lower()
    draft = "yes" if data.get("isDraft") else "no"
    merged_at = str(data.get("mergedAt") or "")
    if state == "merged" or (state == "closed" and merged_at):
        state = "merged"
    return PullRequestState(number, state or "unknown", draft, "")


@dataclass(frozen=True, order=True)
class PullRequestRecord:
    """A single GitHub pull-request result tied to a specific repository."""

    repo: str
    author: str
    url: str


def validate_state(state: str) -> str:
    """Validate *state* against VALID_STATES and return it unchanged."""
    if state not in VALID_STATES:
        raise ValueError("STATE must be one of: open, closed, merged, all")
    return state


def gh_search_args(owner: str, state: str) -> list[str]:
    """Build the ``gh search prs`` argument list for *owner* and *state*."""
    validate_state(state)
    args = [
        "gh",
        "search",
        "prs",
        "--owner",
        owner,
        "--limit",
        "1000",
        "--json",
        "number,title,author,updatedAt,url,isDraft,state,repository",
    ]
    if state == "open":
        args.extend(["--state", "open"])
    elif state == "closed":
        args.extend(["--state", "closed"])
    elif state == "merged":
        args.append("--merged")
    return args


def parse_pull_request_payload(payload: str) -> list[PullRequestRecord]:
    """Parse a JSON *payload* from ``gh search prs`` into PullRequestRecord objects."""
    data = json.loads(payload)
    records: list[PullRequestRecord] = []
    for item in data:
        record = build_pull_request_record(item)
        if record is not None:
            records.append(record)
    return records


def build_pull_request_record(item: dict) -> PullRequestRecord | None:
    """Build a PullRequestRecord from one item in the ``gh search prs`` JSON array.

    Returns None when required fields (repo, author, url) are missing.
    """
    repo = (item.get("repository") or {}).get("nameWithOwner")
    author = (item.get("author") or {}).get("login")
    url = item.get("url")
    if not (repo and author and url):
        return None
    return PullRequestRecord(repo=repo, author=author, url=url)


def filter_managed_pull_requests(
    records: list[PullRequestRecord],
    managed_paths: list[str],
) -> list[PullRequestRecord]:
    """Return sorted, deduplicated PRs belonging to managed repositories."""
    managed = set(managed_repo_slugs(managed_paths))
    return sorted({record for record in records if record.repo in managed})


def render_pull_requests_tsv(records: list[PullRequestRecord]) -> str:
    """Render *records* as a TSV string with a header row."""
    lines = ["repo\tauthor\turl"]
    lines.extend(f"{record.repo}\t{record.author}\t{record.url}" for record in records)
    return "\n".join(lines) + "\n"


# GitHub's mergeStateStatus values that mean "a maintainer can merge this now".
# CLEAN: mergeable, required checks green, branch up to date.
# UNSTABLE: mergeable and required checks green, but some non-required
#           checks are failing or pending.
# HAS_HOOKS: mergeable with passing checks; the repository has pre-receive hooks.
# Everything else (BEHIND, BLOCKED, DIRTY, DRAFT, UNKNOWN) needs work first.
READY_MERGE_STATES = {"CLEAN", "UNSTABLE", "HAS_HOOKS"}


@dataclass(frozen=True, order=True)
class ReadyPullRequestRecord:
    """An open pull request that can be merged as-is."""

    repo: str
    author: str
    merge_state: str
    url: str


def gh_pr_list_args(repo: str) -> list[str]:
    """Build the ``gh pr list`` argument list to inspect mergeability."""
    return [
        "gh",
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--limit",
        "200",
        "--json",
        "author,isDraft,mergeStateStatus,mergeable,url",
    ]


def is_missing_repository_error(message: str) -> bool:
    """Return True when *message* says the repository has no PR support.

    Managed submodules can point at wikis or other checkouts that GitHub's
    pull-request API cannot resolve as repositories. Those should be skipped
    with a warning instead of aborting the whole listing.
    """
    return "could not resolve to a repository" in message.lower()


def parse_ready_pull_requests(payload: str, repo: str) -> list[ReadyPullRequestRecord]:
    """Parse a ``gh pr list`` JSON *payload* and keep only merge-ready PRs."""
    data = json.loads(payload)
    records: list[ReadyPullRequestRecord] = []
    for item in data:
        if item.get("isDraft"):
            continue
        if str(item.get("mergeable") or "") != "MERGEABLE":
            continue
        merge_state = str(item.get("mergeStateStatus") or "")
        if merge_state not in READY_MERGE_STATES:
            continue
        author = (item.get("author") or {}).get("login")
        url = item.get("url")
        if not (author and url):
            continue
        records.append(
            ReadyPullRequestRecord(
                repo=repo,
                author=author,
                merge_state=merge_state,
                url=url,
            ),
        )
    return records


def render_ready_pull_requests_tsv(records: list[ReadyPullRequestRecord]) -> str:
    """Render *records* as a TSV string with a header row."""
    lines = ["repo\tauthor\tmerge_state\turl"]
    lines.extend(
        f"{record.repo}\t{record.author}\t{record.merge_state}\t{record.url}"
        for record in sorted(set(records))
    )
    return "\n".join(lines) + "\n"
