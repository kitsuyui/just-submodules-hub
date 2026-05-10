from __future__ import annotations

import json
from dataclasses import dataclass

from .gitmodules import managed_repo_slugs

VALID_STATES = {"open", "closed", "all"}


@dataclass(frozen=True, order=True)
class IssueRecord:
    repo: str
    author: str
    url: str


def validate_state(state: str) -> str:
    if state not in VALID_STATES:
        raise ValueError("STATE must be one of: open, closed, all")
    return state


def gh_search_args(owner: str, state: str) -> list[str]:
    validate_state(state)
    args = [
        "gh",
        "search",
        "issues",
        "--owner",
        owner,
        "--limit",
        "1000",
        "--json",
        "number,title,author,updatedAt,url,state,repository",
    ]
    if state in {"open", "closed"}:
        args.extend(["--state", state])
    return args


def parse_issue_payload(payload: str) -> list[IssueRecord]:
    data = json.loads(payload)
    records: list[IssueRecord] = []
    for item in data:
        record = build_issue_record(item)
        if record is not None:
            records.append(record)
    return records


def build_issue_record(item: dict) -> IssueRecord | None:
    repo = (item.get("repository") or {}).get("nameWithOwner")
    author = (item.get("author") or {}).get("login")
    url = item.get("url")
    if not (repo and author and url):
        return None
    return IssueRecord(repo=repo, author=author, url=url)


def filter_managed_issues(
    records: list[IssueRecord],
    managed_paths: list[str],
) -> list[IssueRecord]:
    managed = set(managed_repo_slugs(managed_paths))
    return sorted({record for record in records if record.repo in managed})


def render_issues_tsv(records: list[IssueRecord]) -> str:
    lines = ["repo\tauthor\turl"]
    lines.extend(f"{record.repo}\t{record.author}\t{record.url}" for record in records)
    return "\n".join(lines) + "\n"
