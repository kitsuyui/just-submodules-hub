#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.submodule_filters import SubmoduleFilter
from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    run_parallel,
    run_parallel_with_progress,
)


FIELDS = ("repo", "status", "exit_code", "stdout", "stderr")


@dataclass(frozen=True)
class CommandResult:
    repo: str
    status: str
    exit_code: int
    stdout: str
    stderr: str


def compact(text: str) -> str:
    return " ".join(text.strip().split())


def run_one(root: Path, repo_path: str, command: str) -> CommandResult:
    proc = subprocess.run(
        command,
        cwd=str(root / repo_path),
        shell=True,
        text=True,
        capture_output=True,
        check=False,
    )
    return CommandResult(
        repo=repo_path,
        status="ok" if proc.returncode == 0 else "failed",
        exit_code=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )


def shell_command(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return " ".join(shlex.quote(part) for part in parts)


def print_raw(results: list[CommandResult]) -> None:
    first = True
    for result in results:
        if not first:
            print()
        first = False
        print(f"{result.repo}:")
        if result.stdout:
            print(result.stdout, end="" if result.stdout.endswith("\n") else "\n")
        if result.stderr:
            print(f"{result.repo} stderr:", file=sys.stderr)
            print(result.stderr, end="" if result.stderr.endswith("\n") else "\n", file=sys.stderr)


def compact_result(result: CommandResult) -> CommandResult:
    return CommandResult(
        repo=result.repo,
        status=result.status,
        exit_code=result.exit_code,
        stdout=compact(result.stdout),
        stderr=compact(result.stderr),
    )


def parse_args() -> tuple[argparse.Namespace, str]:
    parser = argparse.ArgumentParser(description="Run a shell command for each managed submodule.")
    parser.add_argument("--format", choices=("raw", "table", "tsv", "jsonl"), default="raw")
    parser.add_argument("--jobs", type=positive_int, default=4, help="parallel workers (default: 4)")
    parser.add_argument(
        "--marker-file",
        action="append",
        default=[],
        help="only run the command in submodules containing this marker file; may be repeated",
    )
    args, command_parts = parser.parse_known_args()
    if not command_parts:
        parser.error("COMMAND is required")
    return args, shell_command(command_parts)


def main() -> int:
    args, command = parse_args()
    root = Path.cwd()
    paths = SubmoduleFilter(marker_files=tuple(args.marker_file)).apply(read_gitmodules_paths(root), root)
    if args.format == "raw":
        results, failures = run_parallel(paths, lambda path: run_one(root, path, command), jobs=args.jobs)
    else:
        results, failures = run_parallel_with_progress(
            paths,
            lambda path: run_one(root, path, command),
            jobs=args.jobs,
            desc="every",
            unit="repo",
        )
    results.extend(
        CommandResult(failure.item, "failed", 1, "", failure.message)
        for failure in failures
    )
    results.sort(key=lambda result: result.repo)
    if args.format == "raw":
        print_raw(results)
    else:
        print_records([compact_result(result) for result in results], FIELDS, args.format)
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
