"""List and parse Git linked worktrees for the current repository."""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass

from just_submodules_hub.submodule_batch import print_records

FIELDS = ("path", "head", "branch", "detached", "locked", "prunable", "message")


@dataclass(frozen=True)
class WorktreeRecord:
    """A single Git worktree entry parsed from porcelain output."""

    path: str
    head: str
    branch: str
    detached: str
    locked: str
    prunable: str
    message: str


def short_ref(ref: str) -> str:
    """Strip the refs/heads/ prefix from a branch ref string."""
    return ref.removeprefix("refs/heads/")


def _apply_porcelain_key(
    key: str,
    value: str,
    current: dict[str, str],
) -> None:
    """Apply a single porcelain key-value pair to the current worktree state dict."""
    if key == "HEAD":
        current["head"] = value
    elif key == "branch":
        current["branch"] = short_ref(value)
    elif key == "detached":
        current["detached"] = "yes"
    elif key == "locked":
        current["locked"] = "yes"
        current["locked_reason"] = value
    elif key == "prunable":
        current["prunable"] = "yes"
        current["prunable_reason"] = value
    elif key == "bare":
        current["branch"] = "bare"


def parse_porcelain(text: str) -> list[WorktreeRecord]:
    """Parse git worktree list --porcelain output into a list of WorktreeRecord."""
    records: list[WorktreeRecord] = []
    current: dict[str, str] = {}

    def flush() -> None:
        if not current:
            return
        messages = []
        if current.get("locked_reason"):
            messages.append(f"locked: {current['locked_reason']}")
        if current.get("prunable_reason"):
            messages.append(f"prunable: {current['prunable_reason']}")
        records.append(
            WorktreeRecord(
                path=current.get("path", ""),
                head=current.get("head", ""),
                branch=current.get("branch", ""),
                detached=current.get("detached", "no"),
                locked=current.get("locked", "no"),
                prunable=current.get("prunable", "no"),
                message="; ".join(messages),
            ),
        )

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            flush()
            current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            flush()
            current = {"path": value}
        else:
            _apply_porcelain_key(key, value, current)

    flush()
    return records


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the list-linked-worktrees command."""
    parser = argparse.ArgumentParser(
        description="List Git linked worktrees for the current repository.",
    )
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """List linked worktrees and print them in the requested format."""
    args = parse_args(argv)
    proc = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print(
            (proc.stderr or proc.stdout).strip() or "git worktree list failed",
            file=sys.stderr,
        )
        return proc.returncode

    print_records(parse_porcelain(proc.stdout), FIELDS, args.format)
    return 0
