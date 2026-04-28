#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
from dataclasses import replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.submodule_batch import print_records
from plan_linked_worktree_sync import FIELDS, PlanRecord, default_branch, list_worktrees, plan_one, run_git, summarize


def current_head(repo: Path) -> str:
    proc = run_git(repo, ["rev-parse", "HEAD"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def fetch_target(repo: Path, target: str) -> str:
    if not target.startswith("origin/"):
        return ""
    branch = target.removeprefix("origin/")
    proc = run_git(repo, ["fetch", "origin", branch])
    return "" if proc.returncode == 0 else summarize(proc)


def apply_plan(record: PlanRecord) -> PlanRecord:
    if record.status != "planned":
        return record

    repo = Path(record.path)
    before = current_head(repo)
    fetch_error = fetch_target(repo, record.target)
    if fetch_error:
        return replace(record, status="failed", message=fetch_error)

    if record.action == "pull-default":
        proc = run_git(repo, ["merge", "--ff-only", record.target])
        success_status = "updated"
        success_message = "fast-forwarded"
    elif record.action in ("retire-contained", "retire-merged-pr"):
        proc = run_git(repo, ["switch", "-C", record.branch, record.target])
        success_status = "settled"
        success_message = f"branch reset to {record.target}"
    elif record.action in ("rebase-branch", "rebase-default"):
        proc = run_git(repo, ["rebase", record.target])
        success_status = "updated"
        success_message = f"rebased onto {record.target}"
    else:
        return replace(record, status="failed", message=f"unsupported action: {record.action}")

    if proc.returncode != 0:
        return replace(record, status="failed", message=summarize(proc))

    after = current_head(repo)
    if success_status == "updated" and before and after and before == after:
        return replace(record, status="noop", message="already up to date")
    return replace(record, status=success_status, message=success_message)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Apply safe synchronization decisions for Git linked worktrees.")
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    default = default_branch(root)
    records = [apply_plan(plan_one(worktree, default)) for worktree in list_worktrees(root)]
    print_records(records, FIELDS, args.format)
    return 1 if any(record.status == "failed" for record in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
