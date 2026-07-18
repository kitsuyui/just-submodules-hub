#!/usr/bin/env python3
"""List open pull requests in managed submodules that can be merged as-is."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.github_prs import (
    ActionRequiredPullRequestRecord,
    ReadyPullRequestRecord,
    filter_managed_pull_requests,
    gh_pr_list_args,
    gh_search_args,
    is_missing_repository_error,
    parse_action_required_pull_requests,
    parse_pull_request_payload,
    parse_ready_pull_requests,
    render_action_required_pull_requests_tsv,
    render_ready_pull_requests_tsv,
)
from just_submodules_hub.gitmodules import managed_repo_owners, read_gitmodules_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="List merge-ready pull requests for managed submodules",
    )
    parser.add_argument(
        "--repo-root",
        default=".",
        help="repository root (default: current directory)",
    )
    parser.add_argument(
        "--action-required",
        action="store_true",
        help="list PRs that need an external action instead of merge-ready PRs",
    )
    parser.add_argument(
        "--operator-required",
        action="store_true",
        help="list only action-required PRs that need an operator decision",
    )
    return parser


def check_gh_auth() -> tuple[bool, str]:
    if not shutil.which("gh"):
        return False, "gh command not found"
    proc = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if proc.returncode != 0:
        return False, "gh authentication is invalid. Run: gh auth login -h github.com"
    return True, ""


def list_repository_pull_requests(
    repo_root: Path,
    repo: str,
) -> tuple[str, subprocess.CompletedProcess[str]]:
    """Fetch open pull requests for one managed repository."""
    return repo, subprocess.run(
        gh_pr_list_args(repo),
        cwd=str(repo_root),
        text=True,
        capture_output=True,
    )


def parse_records(
    payload: str,
    repo: str,
    *,
    action_required: bool,
) -> Sequence[ReadyPullRequestRecord | ActionRequiredPullRequestRecord]:
    if action_required:
        return parse_action_required_pull_requests(payload, repo)
    return parse_ready_pull_requests(payload, repo)


def render_records(
    records: list[ReadyPullRequestRecord | ActionRequiredPullRequestRecord],
    *,
    action_required: bool,
    operator_required: bool = False,
) -> str:
    if action_required:
        action_records = [
            record
            for record in records
            if isinstance(record, ActionRequiredPullRequestRecord)
            and (not operator_required or record.operator_required)
        ]
        return render_action_required_pull_requests_tsv(
            action_records,
        )
    return render_ready_pull_requests_tsv(
        [record for record in records if isinstance(record, ReadyPullRequestRecord)],
    )


def main() -> int:
    args = build_parser().parse_args()
    action_listing = args.action_required or args.operator_required

    ok, message = check_gh_auth()
    if not ok:
        print(message, file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root)
    managed_paths = read_gitmodules_paths(repo_root)

    open_pull_requests = []
    for owner in managed_repo_owners(managed_paths):
        proc = subprocess.run(
            gh_search_args(owner, "open"),
            cwd=str(repo_root),
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            print(
                (proc.stderr or proc.stdout).strip() or "gh search prs failed",
                file=sys.stderr,
            )
            return 1
        open_pull_requests.extend(parse_pull_request_payload(proc.stdout))

    candidate_repos = sorted(
        {
            record.repo
            for record in filter_managed_pull_requests(
                open_pull_requests,
                managed_paths,
            )
        },
    )

    records: list[ReadyPullRequestRecord | ActionRequiredPullRequestRecord] = []
    worker_count = min(8, len(candidate_repos))
    if worker_count == 0:
        sys.stdout.write(
            render_records(
                records,
                action_required=action_listing,
                operator_required=args.operator_required,
            ),
        )
        return 0

    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        results = executor.map(
            lambda repo: list_repository_pull_requests(repo_root, repo),
            candidate_repos,
        )

    for repo, proc in results:
        if proc.returncode != 0:
            message = (
                proc.stderr or proc.stdout
            ).strip() or f"gh pr list failed for {repo}"
            if is_missing_repository_error(message):
                print(f"skipping {repo}: no pull-request support", file=sys.stderr)
                continue
            print(message, file=sys.stderr)
            return 1
        records.extend(
            parse_records(proc.stdout, repo, action_required=action_listing),
        )

    sys.stdout.write(
        render_records(
            records,
            action_required=action_listing,
            operator_required=args.operator_required,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
