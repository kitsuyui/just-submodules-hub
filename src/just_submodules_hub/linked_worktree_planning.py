"""Plan safe synchronization decisions for Git linked worktrees."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path

from just_submodules_hub.default_branch import resolve_default_branch as default_branch
from just_submodules_hub.github_prs import PullRequestState, gh_pr_view
from just_submodules_hub.linked_worktree_inventory import (
    WorktreeRecord,
    parse_porcelain,
)
from just_submodules_hub.submodule_batch import print_records

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
    """A single sync-plan record for one linked worktree."""

    path: str
    branch: str
    dirty: str
    pr: str
    draft: str
    status: str
    action: str
    target: str
    message: str


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in *repo* and return the CompletedProcess."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=False,
    )


def summarize(proc: subprocess.CompletedProcess[str]) -> str:
    """Return a one-line summary of a CompletedProcess output."""
    text = (proc.stderr or proc.stdout).strip()
    return " ".join(text.split()) or f"exit {proc.returncode}"


def dirty_state(repo: Path) -> str:
    """Return 'dirty', 'clean', or 'unknown' for the worktree at *repo*."""
    proc = run_git(repo, ["status", "--porcelain"])
    if proc.returncode != 0:
        return "unknown"
    return "dirty" if proc.stdout.strip() else "clean"


def branch_has_unique_commits(repo: Path, branch: str, default: str) -> bool:
    """Return True if *branch* has commits not reachable from origin/<default>."""
    proc = run_git(repo, ["log", "--format=%H", f"origin/{default}..{branch}", "--"])
    if proc.returncode != 0:
        return True
    return bool(proc.stdout.strip())


def remote_branch_exists(repo: Path, branch: str) -> bool:
    """Return True if refs/remotes/origin/<branch> exists in *repo*."""
    proc = run_git(
        repo,
        ["rev-parse", "--verify", "--quiet", f"refs/remotes/origin/{branch}"],
    )
    return proc.returncode == 0


def list_worktrees(root: Path) -> list[WorktreeRecord]:
    """Return all Git linked worktrees registered under *root*."""
    proc = run_git(root, ["worktree", "list", "--porcelain"])
    if proc.returncode != 0:
        raise RuntimeError(summarize(proc))
    return parse_porcelain(proc.stdout)


def _plan_skip_for_worktree_state(
    worktree: WorktreeRecord,
    branch: str,
    dirty: str,
) -> PlanRecord | None:
    """Return a skip/failed PlanRecord for bad worktree states.

    Returns None if OK to proceed.
    """
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
    return None


def _plan_record_for_pr(
    worktree: WorktreeRecord,
    branch: str,
    dirty: str,
    pr: PullRequestState,
    default: str,
) -> PlanRecord:
    """Resolve a PlanRecord based on the pull request state for *branch*."""
    repo = Path(worktree.path)
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


def plan_one(worktree: WorktreeRecord, default: str) -> PlanRecord:
    """Plan the synchronization action for a single linked worktree."""
    repo = Path(worktree.path)
    branch = worktree.branch
    dirty = dirty_state(repo)

    skip = _plan_skip_for_worktree_state(worktree, branch, dirty)
    if skip is not None:
        return skip

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
    return _plan_record_for_pr(worktree, branch, dirty, pr, default)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for plan-linked-worktree-sync."""
    parser = argparse.ArgumentParser(
        description="Plan safe synchronization decisions for Git linked worktrees.",
    )
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Plan sync decisions for all linked worktrees and print a report."""
    args = parse_args(argv)
    root = Path.cwd()
    resolved_default = default_branch(root)
    records = [
        plan_one(worktree, resolved_default) for worktree in list_worktrees(root)
    ]
    print_records(records, FIELDS, args.format)
    return 1 if any(record.status == "failed" for record in records) else 0
