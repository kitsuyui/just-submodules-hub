"""Action handlers for managing git linked worktrees."""

from __future__ import annotations

import contextlib
import os
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

from just_submodules_hub.run_action.actions._helpers import validate_positive_integer
from just_submodules_hub.run_action.registry import action, dispatch

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
_SAFETY_SCRIPT = _PROJECT_ROOT / "scripts" / "repo" / "linked_worktree_safety.py"


@contextlib.contextmanager
def _chdir(path: str) -> Generator[None]:
    """Context manager: temporarily change the working directory."""
    old = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)


def _run_safety(subcommand: str, args: list[str]) -> int:
    """Run linked_worktree_safety.py <subcommand> [args...] via uv."""
    cmd = [
        "uv",
        "run",
        "--project",
        str(_PROJECT_ROOT),
        "python",
        str(_SAFETY_SCRIPT),
        subcommand,
        *args,
    ]
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


@action("install-linked-worktree-hooks")
def install_linked_worktree_hooks(args: list[str]) -> int:
    """Install git hooks needed by linked-worktree safety checks."""
    return _run_safety("install-hooks", args)


@action("reset-linked-worktree")
def reset_linked_worktree(args: list[str]) -> int:
    """Reset a linked worktree to a clean state."""
    return _run_safety("reset", args)


@action("cleanup-linked-worktrees")
def cleanup_linked_worktrees(args: list[str]) -> int:
    """Remove stale linked worktrees that no longer have a corresponding branch."""
    return _run_safety("cleanup", args)


@action("remove-linked-worktree")
def remove_linked_worktree(args: list[str]) -> int:
    """Remove a specific linked worktree by path."""
    worktree_path = args[0] if args else ""
    if not worktree_path:
        print("PATH is required", file=sys.stderr)
        return 2
    rest = args[1:]

    force = False
    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg in ("--force", "-f"):
            force = True
        elif arg.startswith("--"):
            print(f"unknown linked worktree remove option: {arg}", file=sys.stderr)
            return 2
        else:
            print(f"unexpected linked worktree remove argument: {arg}", file=sys.stderr)
            return 2
        i += 1

    cmd = ["git", "worktree", "remove"]
    if force:
        cmd.append("--force")
    cmd.append(worktree_path)
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def _build_worktree_add_cmd(
    worktree_path: str,
    branch: str,
    start_point: str,
) -> list[str]:
    """Build the git worktree add command from parsed arguments."""
    cmd = ["git", "worktree", "add"]
    if branch and start_point:
        cmd.extend(["-b", branch, worktree_path, start_point])
    elif branch:
        cmd.extend(["-b", branch, worktree_path])
    elif start_point:
        cmd.extend([worktree_path, start_point])
    else:
        cmd.append(worktree_path)
    return cmd


def _build_init_submodule_args(
    init_mode: str,
    init_jobs: str,
) -> list[str] | None:
    """Build init-all-repos args from mode and jobs strings.

    Returns None when *init_mode* is unrecognized.
    """
    init_args: list[str] = ["--force"]
    if init_mode == "fetch-fallback":
        init_args.append("--fetch-fallback")
    elif init_mode == "no-fetch":
        init_args.append("--no-fetch")
    elif init_mode != "normal":
        return None
    if init_jobs:
        init_args.extend(["--jobs", init_jobs])
    return init_args


def _parse_add_linked_worktree_rest(  # noqa: C901  # arg-aliases: --no-fetch/--submodule-no-fetch etc.
    rest: list[str],
) -> tuple[str, str, bool, str, str] | None:
    """Parse the optional arguments for add-linked-worktree.

    Returns ``(branch, start_point, init_submodules, init_mode, init_jobs)``
    or ``None`` on error (error message already printed).
    """
    branch = ""
    start_point = ""
    init_submodules = True
    init_mode = "normal"
    init_jobs = ""

    i = 0
    while i < len(rest):
        arg = rest[i]
        if arg in ("--branch", "-b"):
            i += 1
            if i >= len(rest) or not rest[i]:
                print("--branch requires a value", file=sys.stderr)
                return None
            branch = rest[i]
        elif arg.startswith("--branch="):
            branch = arg[len("--branch=") :]
        elif arg == "--start-point":
            i += 1
            if i >= len(rest) or not rest[i]:
                print("--start-point requires a value", file=sys.stderr)
                return None
            start_point = rest[i]
        elif arg.startswith("--start-point="):
            start_point = arg[len("--start-point=") :]
        elif arg == "--no-submodules":
            init_submodules = False
        elif arg in ("--no-fetch", "--submodule-no-fetch"):
            init_mode = "no-fetch"
        elif arg in ("--fetch-fallback", "--submodule-fetch-fallback"):
            init_mode = "fetch-fallback"
        elif arg in ("--jobs", "--submodule-jobs"):
            option_name = arg
            i += 1
            if i >= len(rest) or not rest[i]:
                print(f"{option_name} requires a value", file=sys.stderr)
                return None
            init_jobs = rest[i]
        elif arg.startswith("--jobs=") or arg.startswith("--submodule-jobs="):
            init_jobs = arg.split("=", 1)[1]
        elif arg.startswith("--"):
            print(f"unknown linked worktree add option: {arg}", file=sys.stderr)
            return None
        else:
            if start_point:
                print(
                    f"unexpected linked worktree add argument: {arg}",
                    file=sys.stderr,
                )
                return None
            start_point = arg
        i += 1

    return branch, start_point, init_submodules, init_mode, init_jobs


@action("add-linked-worktree")
def add_linked_worktree(args: list[str]) -> int:
    """Create a new linked worktree with optional submodule initialization."""
    if not args or not args[0]:
        print("PATH is required", file=sys.stderr)
        return 2

    worktree_path = args[0]
    parsed = _parse_add_linked_worktree_rest(args[1:])
    if parsed is None:
        return 2

    branch, start_point, init_submodules, init_mode, init_jobs = parsed

    if init_jobs:
        rc = validate_positive_integer(init_jobs, "JOBS")
        if rc != 0:
            return rc

    git_cmd = _build_worktree_add_cmd(worktree_path, branch, start_point)
    proc = subprocess.run(git_cmd, check=False)
    if proc.returncode != 0:
        return proc.returncode

    if not init_submodules:
        return 0

    init_args = _build_init_submodule_args(init_mode, init_jobs)
    if init_args is None:
        print(f"unknown submodule init mode: {init_mode}", file=sys.stderr)
        return 2

    with _chdir(worktree_path):
        return dispatch("init-all-repos", init_args)
