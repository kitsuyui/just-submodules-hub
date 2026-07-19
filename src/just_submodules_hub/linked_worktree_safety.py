"""Linked worktree safety helpers: hooks, reset, and cleanup."""

from __future__ import annotations

import argparse
import fnmatch
import re
import stat
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from just_submodules_hub.default_branch import resolve_default_branch as default_branch
from just_submodules_hub.linked_worktree_planning import (
    PlanRecord,  # noqa: F401 - re-exported for downstream consumers
    WorktreeRecord,
    dirty_state,
    list_worktrees,
    plan_one,
    run_git,
    summarize,
)
from just_submodules_hub.submodule_batch import positive_int, print_records

HOOK_FIELDS = ("status", "path", "message")
RESET_FIELDS = ("path", "branch", "status", "action", "backup", "target", "message")
CLEANUP_FIELDS = ("path", "branch", "status", "action", "message")

PRE_PUSH_HOOK = """#!/bin/sh
while read -r local_ref local_sha remote_ref remote_sha; do
  case "$local_ref" in
    refs/heads/worktree/*)
      echo "refusing to push local-only linked worktree branch: $local_ref" >&2
      exit 1
      ;;
  esac
done
exit 0
"""


@dataclass(frozen=True)
class HookRecord:
    """Result of a hook-installation attempt."""

    status: str
    path: str
    message: str


@dataclass(frozen=True)
class ResetRecord:
    """Result of a worktree-reset attempt."""

    path: str
    branch: str
    status: str
    action: str
    backup: str
    target: str
    message: str


@dataclass(frozen=True)
class CleanupRecord:
    """Result of a worktree-cleanup evaluation."""

    path: str
    branch: str
    status: str
    action: str
    message: str


def timestamp() -> str:
    """Return the current UTC time as a compact sortable string."""
    return datetime.now(UTC).strftime("%Y%m%d%H%M%S")


def sanitize_ref_component(raw: str) -> str:
    """Sanitize *raw* for use as a Git ref path component."""
    value = raw.strip().strip("/").replace("/", "-")
    value = re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-")
    return value or "worktree"


def git_common_dir(root: Path) -> Path:
    """Return the git common dir for the repository rooted at *root*."""
    proc = run_git(root, ["rev-parse", "--git-common-dir"])
    if proc.returncode != 0:
        raise RuntimeError(summarize(proc))
    value = Path(proc.stdout.strip())
    if value.is_absolute():
        return value
    return root / value


def install_hooks(root: Path) -> HookRecord:
    """Install the pre-push safety hook in the repository at *root*."""
    hooks_dir = git_common_dir(root) / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook_path = hooks_dir / "pre-push"
    if hook_path.exists():
        sample_path = hooks_dir / "pre-push.linked-worktrees.sample"
        if not sample_path.exists():
            sample_path.write_text(PRE_PUSH_HOOK, encoding="utf-8")
            sample_path.chmod(sample_path.stat().st_mode | stat.S_IXUSR)
            return HookRecord(
                "skipped",
                str(hook_path),
                f"existing hook kept; wrote sample to {sample_path}",
            )
        return HookRecord("skipped", str(hook_path), "existing hook kept")
    hook_path.write_text(PRE_PUSH_HOOK, encoding="utf-8")
    hook_path.chmod(hook_path.stat().st_mode | stat.S_IXUSR)
    return HookRecord("installed", str(hook_path), "pre-push hook installed")


def current_branch(repo: Path) -> str:
    """Return the current branch name for *repo*, or empty string."""
    proc = run_git(repo, ["branch", "--show-current"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def current_head(repo: Path) -> str:
    """Return the current HEAD commit hash for *repo*, or empty string."""
    proc = run_git(repo, ["rev-parse", "HEAD"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def reset_record(
    repo: Path,
    *,
    target: str,
    backup_prefix: str,
    apply: bool,
) -> ResetRecord:
    """Plan or apply a reset for one linked worktree."""
    branch = current_branch(repo)
    if not branch:
        return ResetRecord(
            str(repo),
            "",
            "skipped",
            "skip-detached",
            "",
            target,
            "detached HEAD",
        )
    dirty = dirty_state(repo)
    if dirty == "dirty":
        return ResetRecord(
            str(repo),
            branch,
            "skipped",
            "skip-dirty",
            "",
            target,
            "worktree has local changes",
        )
    if dirty == "unknown":
        return ResetRecord(
            str(repo),
            branch,
            "failed",
            "inspect",
            "",
            target,
            "cannot inspect worktree status",
        )
    resolved_target = target or f"origin/{default_branch(repo)}"
    backup = f"{backup_prefix}/{sanitize_ref_component(Path(repo).name)}/{timestamp()}"
    if not apply:
        return ResetRecord(
            str(repo),
            branch,
            "planned",
            "reset",
            backup,
            resolved_target,
            "dry-run",
        )
    if resolved_target.startswith("origin/"):
        fetched = run_git(
            repo,
            ["fetch", "origin", resolved_target.removeprefix("origin/")],
        )
        if fetched.returncode != 0:
            return ResetRecord(
                str(repo),
                branch,
                "failed",
                "fetch-target",
                backup,
                resolved_target,
                summarize(fetched),
            )
    head = current_head(repo)
    if not head:
        return ResetRecord(
            str(repo),
            branch,
            "failed",
            "inspect",
            backup,
            resolved_target,
            "cannot resolve HEAD",
        )
    backup_proc = run_git(repo, ["branch", backup, head])
    if backup_proc.returncode != 0:
        return ResetRecord(
            str(repo),
            branch,
            "failed",
            "backup",
            backup,
            resolved_target,
            summarize(backup_proc),
        )
    reset_proc = run_git(repo, ["switch", "-C", branch, resolved_target])
    if reset_proc.returncode != 0:
        return ResetRecord(
            str(repo),
            branch,
            "failed",
            "reset",
            backup,
            resolved_target,
            summarize(reset_proc),
        )
    return ResetRecord(
        str(repo),
        branch,
        "settled",
        "reset",
        backup,
        resolved_target,
        "branch reset with backup",
    )


def path_matches(path: str, pattern: str) -> bool:
    """Return True if *path* matches *pattern* by full path or basename glob."""
    return fnmatch.fnmatch(path, pattern) or fnmatch.fnmatch(Path(path).name, pattern)


def _cleanup_one_worktree(
    root: Path,
    worktree: WorktreeRecord,
    default: str,
    *,
    apply: bool,
    drop_branch: bool,
    include_skipped: bool,
) -> list[CleanupRecord]:
    """Process a single worktree for cleanup; return zero or one CleanupRecord."""
    plan = plan_one(worktree, default)
    if plan.action not in ("retire-contained", "retire-merged-pr"):
        if include_skipped:
            return [
                CleanupRecord(
                    worktree.path, worktree.branch, "skipped", plan.action, plan.message
                )
            ]
        return []
    if not apply:
        return [
            CleanupRecord(
                worktree.path, worktree.branch, "planned", "remove", "dry-run"
            )
        ]
    remove_proc = run_git(root, ["worktree", "remove", worktree.path])
    if remove_proc.returncode != 0:
        return [
            CleanupRecord(
                worktree.path,
                worktree.branch,
                "failed",
                "remove",
                summarize(remove_proc),
            )
        ]
    if drop_branch and worktree.branch:
        drop_proc = run_git(root, ["branch", "-D", worktree.branch])
        if drop_proc.returncode != 0:
            return [
                CleanupRecord(
                    worktree.path,
                    worktree.branch,
                    "failed",
                    "drop-branch",
                    summarize(drop_proc),
                )
            ]
    return [
        CleanupRecord(
            worktree.path, worktree.branch, "removed", "remove", "worktree removed"
        )
    ]


def cleanup_records(
    root: Path,
    *,
    path_glob: str,
    apply: bool,
    drop_branch: bool,
    include_skipped: bool,
    jobs: int = 8,
) -> list[CleanupRecord]:
    """Collect cleanup records for all matched linked worktrees under *root*."""
    resolved_default = default_branch(root)
    rows: list[CleanupRecord] = []
    root_resolved = root.resolve()
    matched: list[WorktreeRecord] = []
    for worktree in list_worktrees(root):
        if Path(worktree.path).resolve() == root_resolved:
            continue
        if not path_matches(worktree.path, path_glob):
            if include_skipped:
                rows.append(
                    CleanupRecord(
                        worktree.path,
                        worktree.branch,
                        "skipped",
                        "skip-path",
                        "path does not match glob",
                    ),
                )
            continue
        matched.append(worktree)

    def cleanup_one(worktree: WorktreeRecord) -> list[CleanupRecord]:
        return _cleanup_one_worktree(
            root,
            worktree,
            resolved_default,
            apply=apply,
            drop_branch=drop_branch,
            include_skipped=include_skipped,
        )

    if apply:
        for worktree in matched:
            rows.extend(cleanup_one(worktree))
        return rows
    worker_count = min(jobs, len(matched))
    if worker_count == 0:
        return rows
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        planned = list(executor.map(cleanup_one, matched))
    for records in planned:
        rows.extend(records)
    return rows


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the linked-worktree safety helpers."""
    parser = argparse.ArgumentParser(description="Linked worktree safety helpers.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    hooks = subparsers.add_parser(
        "install-hooks",
        help="install linked worktree safety hooks",
    )
    hooks.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")

    reset = subparsers.add_parser(
        "reset",
        help="plan or apply a reset for one linked worktree",
    )
    reset.add_argument("path")
    reset.add_argument("--target", default="")
    reset.add_argument("--backup-prefix", default="stash")
    reset.add_argument("--apply", action="store_true")
    reset.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")

    cleanup = subparsers.add_parser(
        "cleanup",
        help="plan or apply cleanup of safe linked worktree candidates",
    )
    cleanup.add_argument("--path-glob", required=True)
    cleanup.add_argument("--apply", action="store_true")
    cleanup.add_argument("--drop-branch", action="store_true")
    cleanup.add_argument("--include-skipped", action="store_true")
    cleanup.add_argument("--jobs", type=positive_int, default=8)
    cleanup.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")

    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Dispatch to the requested linked-worktree safety subcommand."""
    args = parse_args(argv)
    root = Path.cwd()
    records: Sequence[HookRecord | ResetRecord | CleanupRecord]
    fields: Sequence[str]
    if args.command == "install-hooks":
        records = [install_hooks(root)]
        fields = HOOK_FIELDS
    elif args.command == "reset":
        records = [
            reset_record(
                Path(args.path),
                target=args.target,
                backup_prefix=args.backup_prefix,
                apply=args.apply,
            ),
        ]
        fields = RESET_FIELDS
    else:
        records = cleanup_records(
            root,
            path_glob=args.path_glob,
            apply=args.apply,
            drop_branch=args.drop_branch,
            include_skipped=args.include_skipped,
            jobs=args.jobs,
        )
        fields = CLEANUP_FIELDS
    print_records(records, fields, args.format)
    return 1 if any(record.status == "failed" for record in records) else 0
