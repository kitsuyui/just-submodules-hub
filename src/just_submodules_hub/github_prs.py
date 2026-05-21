"""GitHub Pull Request search and filtering helpers."""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

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
    proc = subprocess.run(
        ["gh", "pr", "view", "--json", "number,state,isDraft,mergedAt"],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
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
