"""Apply safe synchronization decisions for Git linked worktrees."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

from just_submodules_hub.default_branch import resolve_default_branch as default_branch
from just_submodules_hub.linked_worktree_planning import (
    FIELDS,
    PlanRecord,
    list_worktrees,
    plan_one,
    run_git,
    summarize,
)
from just_submodules_hub.submodule_batch import print_records


def current_head(repo: Path) -> str:
    """Return the current HEAD commit hash for *repo*, or empty string on failure."""
    proc = run_git(repo, ["rev-parse", "HEAD"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def fetch_target(repo: Path, target: str) -> str:
    """Fetch *target* from origin if it begins with 'origin/'.

    Returns an error message string, or empty string on success.
    """
    if not target.startswith("origin/"):
        return ""
    branch = target.removeprefix("origin/")
    proc = run_git(repo, ["fetch", "origin", branch])
    return "" if proc.returncode == 0 else summarize(proc)


def apply_plan(record: PlanRecord) -> PlanRecord:
    """Apply the planned action to a single linked worktree record."""
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
        if proc.returncode != 0:
            # Rebase failed (typically a conflict). Best-effort abort so the
            # worktree is not left in REBASING state with conflict markers,
            # which would block subsequent runs and confuse users.
            abort_proc = run_git(repo, ["rebase", "--abort"])
            suffix = "; rebase aborted" if abort_proc.returncode == 0 else ""
            return replace(
                record,
                status="failed",
                message=f"{summarize(proc)}{suffix}",
            )
        success_status = "updated"
        success_message = f"rebased onto {record.target}"
    else:
        return replace(
            record,
            status="failed",
            message=f"unsupported action: {record.action}",
        )

    if proc.returncode != 0:
        return replace(record, status="failed", message=summarize(proc))

    after = current_head(repo)
    if success_status == "updated" and before and after and before == after:
        return replace(record, status="noop", message="already up to date")
    return replace(record, status=success_status, message=success_message)


def read_plan_from_stdin() -> list[PlanRecord]:
    """Read JSONL-formatted PlanRecord entries from stdin."""
    records: list[PlanRecord] = []
    for lineno, raw in enumerate(sys.stdin, start=1):
        line = raw.rstrip("\n")
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as exc:
            print(
                f"line {lineno}: invalid JSON ({exc}): {line!r}",
                file=sys.stderr,
            )
            raise SystemExit(2) from exc
        records.append(PlanRecord(**{k: data.get(k, "") for k in FIELDS}))
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for apply-linked-worktree-sync."""
    parser = argparse.ArgumentParser(
        description="Apply safe synchronization decisions for Git linked worktrees.",
    )
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    parser.add_argument(
        "--from-plan-stdin",
        action="store_true",
        help="Read plan records as JSONL from stdin instead of recomputing the plan.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Apply sync decisions to all linked worktrees and print a report."""
    args = parse_args(argv)
    if args.from_plan_stdin:
        plan_records = read_plan_from_stdin()
    else:
        root = Path.cwd()
        resolved_default = default_branch(root)
        plan_records = [
            plan_one(worktree, resolved_default) for worktree in list_worktrees(root)
        ]
    records = [apply_plan(record) for record in plan_records]
    print_records(records, FIELDS, args.format)
    return 1 if any(record.status == "failed" for record in records) else 0
