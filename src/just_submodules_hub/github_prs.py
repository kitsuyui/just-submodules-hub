from __future__ import annotations

import json
from dataclasses import dataclass

from .gitmodules import managed_repo_slugs


VALID_STATES = {"open", "closed", "merged", "all"}


@dataclass(frozen=True, order=True)
class PullRequestRecord:
    repo: str
    author: str
    url: str


def validate_state(state: str) -> str:
    if state not in VALID_STATES:
        raise ValueError("STATE must be one of: open, closed, merged, all")
    return state


def gh_search_args(owner: str, state: str) -> list[str]:
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
    data = json.loads(payload)
    records: list[PullRequestRecord] = []
    for item in data:
        repo = (item.get("repository") or {}).get("nameWithOwner")
        author = (item.get("author") or {}).get("login")
        url = item.get("url")
        if repo and author and url:
            records.append(PullRequestRecord(repo=repo, author=author, url=url))
    return records


def filter_managed_pull_requests(records: list[PullRequestRecord], managed_paths: list[str]) -> list[PullRequestRecord]:
    managed = set(managed_repo_slugs(managed_paths))
    return sorted({record for record in records if record.repo in managed})


def render_pull_requests_tsv(records: list[PullRequestRecord]) -> str:
    lines = ["repo\tauthor\turl"]
    lines.extend(f"{record.repo}\t{record.author}\t{record.url}" for record in records)
    return "\n".join(lines) + "\n"
