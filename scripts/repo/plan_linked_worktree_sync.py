#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.default_branch import resolve_default_branch as default_branch
from just_submodules_hub.submodule_batch import print_records
from list_linked_worktrees import WorktreeRecord, parse_porcelain


FIELDS = (
    "path",
    "branch",
    "dirty",
    "pr",
    "draft",
    "status",
    "action",
    "target",
    "message",
)


@dataclass(frozen=True)
class PlanRecord:
    path: str
    branch: str
    dirty: str
    pr: str
    draft: str
    status: str
    action: str
    target: str
    message: str


@dataclass(frozen=True)
class PullRequestState:
    number: str
    state: str
    draft: str
    message: str


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args], text=True, capture_output=True, check=False
    )


def summarize(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout).strip()
    return " ".join(text.split()) or f"exit {proc.returncode}"


def dirty_state(repo: Path) -> str:
    proc = run_git(repo, ["status", "--porcelain"])
    if proc.returncode != 0:
        return "unknown"
    return "dirty" if proc.stdout.strip() else "clean"


def branch_has_unique_commits(repo: Path, branch: str, default: str) -> bool:
    proc = run_git(repo, ["log", "--format=%H", f"origin/{default}..{branch}", "--"])
    if proc.returncode != 0:
        return True
    return bool(proc.stdout.strip())


def remote_branch_exists(repo: Path, branch: str) -> bool:
    proc = run_git(
        repo, ["rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"]
    )
    return proc.returncode == 0


def gh_pr_view(repo: Path) -> PullRequestState:
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
        message = summarize(proc)
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


def list_worktrees(root: Path) -> list[WorktreeRecord]:
    proc = run_git(root, ["worktree", "list", "--porcelain"])
    if proc.returncode != 0:
        raise RuntimeError(summarize(proc))
    return parse_porcelain(proc.stdout)


def plan_one(worktree: WorktreeRecord, default: str) -> PlanRecord:
    repo = Path(worktree.path)
    branch = worktree.branch
    dirty = dirty_state(repo)

    if worktree.locked == "yes":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "skipped",
            "skip-locked",
            "",
            worktree.message,
        )
    if worktree.prunable == "yes":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "skipped",
            "skip-prunable",
            "",
            worktree.message,
        )
    if dirty == "dirty":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "skipped",
            "skip-dirty",
            "",
            "worktree has local changes",
        )
    if dirty == "unknown":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "failed",
            "inspect",
            "",
            "cannot inspect worktree status",
        )
    if worktree.detached == "yes" or not branch:
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "skipped",
            "skip-detached",
            "",
            "detached HEAD",
        )
    if branch == default:
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "planned",
            "pull-default",
            f"origin/{default}",
            "default branch",
        )
    if not branch_has_unique_commits(repo, branch, default):
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            "",
            "",
            "planned",
            "retire-contained",
            f"origin/{default}",
            "branch has no commits outside default branch",
        )

    pr = gh_pr_view(repo)
    if pr.state == "unknown":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            pr.number,
            pr.draft,
            "skipped",
            "skip-pr-unknown",
            "",
            pr.message,
        )
    if pr.state == "open" and pr.draft != "yes":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            pr.number,
            pr.draft,
            "skipped",
            "skip-open-pr",
            "",
            "open non-draft pull request",
        )
    if pr.state == "closed":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            pr.number,
            pr.draft,
            "skipped",
            "skip-closed-pr",
            "",
            "pull request closed without merge",
        )
    if pr.state == "merged":
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            pr.number,
            pr.draft,
            "planned",
            "retire-merged-pr",
            f"origin/{default}",
            "pull request is merged",
        )

    if remote_branch_exists(repo, branch):
        return PlanRecord(
            worktree.path,
            branch,
            dirty,
            pr.number,
            pr.draft,
            "planned",
            "rebase-branch",
            f"origin/{branch}",
            "draft PR or private branch with remote tracking branch",
        )
    return PlanRecord(
        worktree.path,
        branch,
        dirty,
        pr.number,
        pr.draft,
        "planned",
        "rebase-default",
        f"origin/{default}",
        "draft PR or private branch without remote tracking branch",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan safe synchronization decisions for Git linked worktrees."
    )
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    default = default_branch(root)
    records = [plan_one(worktree, default) for worktree in list_worktrees(root)]
    print_records(records, FIELDS, args.format)
    return 1 if any(record.status == "failed" for record in records) else 0


if __name__ == "__main__":
    raise SystemExit(main())
