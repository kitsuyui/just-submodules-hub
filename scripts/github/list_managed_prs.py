#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.github_prs import (
    filter_managed_pull_requests,
    gh_search_args,
    parse_pull_request_payload,
    render_pull_requests_tsv,
    validate_state,
)
from just_submodules_hub.gitmodules import managed_repo_owners, read_gitmodules_paths


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List pull requests for managed submodules")
    parser.add_argument("state", nargs="?", default="open", help="open, closed, merged, or all")
    parser.add_argument("--repo-root", default=".", help="repository root (default: current directory)")
    return parser


def check_gh_auth() -> tuple[bool, str]:
    if not shutil_which("gh"):
        return False, "gh command not found"
    proc = subprocess.run(["gh", "auth", "status"], text=True, capture_output=True)
    if proc.returncode != 0:
        return False, "gh authentication is invalid. Run: gh auth login -h github.com"
    return True, ""


def shutil_which(cmd: str) -> str | None:
    from shutil import which

    return which(cmd)


def main() -> int:
    args = build_parser().parse_args()
    try:
        state = validate_state(args.state)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    ok, message = check_gh_auth()
    if not ok:
        print(message, file=sys.stderr)
        return 1

    repo_root = Path(args.repo_root)
    managed_paths = read_gitmodules_paths(repo_root)
    owners = managed_repo_owners(managed_paths)

    records = []
    for owner in owners:
        proc = subprocess.run(
            gh_search_args(owner, state),
            cwd=str(repo_root),
            text=True,
            capture_output=True,
        )
        if proc.returncode != 0:
            print((proc.stderr or proc.stdout).strip() or "gh search prs failed", file=sys.stderr)
            return 1
        records.extend(parse_pull_request_payload(proc.stdout))

    sys.stdout.write(render_pull_requests_tsv(filter_managed_pull_requests(records, managed_paths)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
