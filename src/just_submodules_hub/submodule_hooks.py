"""Install repository-local Git hook managers in managed submodules."""

from __future__ import annotations

import argparse
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from shutil import which

from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    run_parallel_with_progress,
)
from just_submodules_hub.submodule_filters import SubmoduleFilter

MANAGERS = ("lefthook", "pre-commit", "husky")
FIELDS = ("repo", "status", "manager", "command", "exit_code", "stdout", "stderr")


@dataclass(frozen=True)
class HookInstallResult:
    """Structured result for one submodule hook setup attempt."""

    repo: str
    status: str
    manager: str
    command: str
    exit_code: int
    stdout: str
    stderr: str


def compact(text: str) -> str:
    """Return *text* as one line for structured command output."""
    return " ".join(text.strip().split())


def has_any(path: Path, names: tuple[str, ...]) -> bool:
    """Return True when *path* contains any file or directory in *names*."""
    return any((path / name).exists() for name in names)


def detect_managers(repo: Path) -> list[str]:
    """Detect supported Git hook managers configured in *repo*."""
    managers: list[str] = []
    if has_any(
        repo,
        ("lefthook.yml", "lefthook.yaml", ".lefthook.yml", ".lefthook.yaml"),
    ):
        managers.append("lefthook")
    if has_any(repo, (".pre-commit-config.yaml", ".pre-commit-config.yml")):
        managers.append("pre-commit")
    if (repo / ".husky").is_dir():
        managers.append("husky")
    return managers


def resolve_manager(repo: Path, requested: str) -> tuple[str, str]:
    """Resolve the hook manager to install.

    Returns ``(manager, reason)``. ``manager`` is empty when there is nothing to
    install or when the repository is ambiguous.
    """
    detected = detect_managers(repo)
    if requested != "auto":
        return (requested, "") if requested in detected else ("", "not-configured")
    if not detected:
        return "", "no-config"
    if len(detected) > 1:
        return "", "ambiguous:" + ",".join(detected)
    return detected[0], ""


def executable_command(repo: Path, name: str) -> list[str] | None:
    """Return a command for *name*, preferring local project binaries."""
    local = repo / "node_modules" / ".bin" / name
    if local.exists():
        return [str(local)]
    if path := shutil_which(name):
        return [path]
    return None


def shutil_which(name: str) -> str | None:
    """Small wrapper to keep command lookup easy to monkeypatch in tests."""
    return which(name)


def install_command(repo: Path, manager: str) -> list[str] | None:
    """Return the command that installs *manager* in *repo*."""
    if manager == "lefthook":
        command = executable_command(repo, "lefthook")
        return [*command, "install"] if command else None
    if manager == "pre-commit":
        command = executable_command(repo, "pre-commit")
        return [*command, "install"] if command else None
    if manager == "husky":
        if (repo / ".husky" / "_").is_dir():
            return ["git", "config", "core.hooksPath", ".husky/_"]
        return executable_command(repo, "husky")
    raise ValueError(f"unsupported manager: {manager}")


def dry_run_command(repo: Path, manager: str) -> list[str]:
    """Return the canonical command label for dry-run output."""
    if manager == "lefthook":
        return ["lefthook", "install"]
    if manager == "pre-commit":
        return ["pre-commit", "install"]
    if manager == "husky":
        if (repo / ".husky" / "_").is_dir():
            return ["git", "config", "core.hooksPath", ".husky/_"]
        return ["husky"]
    raise ValueError(f"unsupported manager: {manager}")


def command_label(command: list[str]) -> str:
    """Return a compact human-readable command label."""
    parts = [
        Path(part).name if index == 0 else part for index, part in enumerate(command)
    ]
    return " ".join(parts)


def run_one(
    root: Path,
    repo_path: str,
    *,
    manager: str,
    dry_run: bool,
) -> HookInstallResult:
    """Install a detected hook manager in one submodule."""
    repo = root / repo_path
    selected, reason = resolve_manager(repo, manager)
    if not selected:
        status = "noop" if reason in {"no-config", "not-configured"} else "failed"
        exit_code = 0 if status == "noop" else 1
        return HookInstallResult(repo_path, status, reason, "", exit_code, "", "")

    if dry_run:
        label = command_label(dry_run_command(repo, selected))
        return HookInstallResult(repo_path, "would-install", selected, label, 0, "", "")

    command = install_command(repo, selected)
    if command is None:
        return HookInstallResult(
            repo_path,
            "failed",
            selected,
            "",
            127,
            "",
            f"{selected} command not found",
        )

    label = command_label(command)
    env = os.environ.copy()
    env.setdefault("HUSKY", "1")
    proc = subprocess.run(
        command,
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    return HookInstallResult(
        repo_path,
        "installed" if proc.returncode == 0 else "failed",
        selected,
        label,
        proc.returncode,
        compact(proc.stdout),
        compact(proc.stderr),
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        description="Install configured Git hook managers in managed submodules.",
    )
    parser.add_argument(
        "--format",
        choices=("table", "tsv", "jsonl"),
        default="table",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=4,
        help="parallel workers (default: 4)",
    )
    parser.add_argument(
        "--manager",
        choices=("auto", *MANAGERS),
        default="auto",
        help="hook manager to install (default: auto-detect)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="report detected hook setup commands without running them",
    )
    parser.add_argument(
        "--marker-file",
        action="append",
        default=[],
        help=("only inspect submodules containing this marker file; may be repeated"),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = build_parser().parse_args(argv)
    root = Path.cwd()
    paths = SubmoduleFilter(marker_files=tuple(args.marker_file)).apply(
        read_gitmodules_paths(root),
        root,
    )
    results, failures = run_parallel_with_progress(
        paths,
        lambda path: run_one(
            root,
            path,
            manager=args.manager,
            dry_run=args.dry_run,
        ),
        jobs=args.jobs,
        desc="hooks",
        unit="repo",
        enabled=args.format != "jsonl",
    )
    results.extend(
        HookInstallResult(failure.item, "failed", "worker", "", 1, "", failure.message)
        for failure in failures
    )
    results.sort(key=lambda result: result.repo)
    print_records(results, FIELDS, args.format)
    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
