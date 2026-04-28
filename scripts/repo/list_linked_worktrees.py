#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.submodule_batch import print_records


FIELDS = ("path", "head", "branch", "detached", "locked", "prunable", "message")


@dataclass(frozen=True)
class WorktreeRecord:
    path: str
    head: str
    branch: str
    detached: str
    locked: str
    prunable: str
    message: str


def short_ref(ref: str) -> str:
    return ref.removeprefix("refs/heads/")


def parse_porcelain(text: str) -> list[WorktreeRecord]:
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
            )
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
        elif key == "HEAD":
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

    flush()
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="List Git linked worktrees for the current repository.")
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    proc = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        print((proc.stderr or proc.stdout).strip() or "git worktree list failed", file=sys.stderr)
        return proc.returncode

    print_records(parse_porcelain(proc.stdout), FIELDS, args.format)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
