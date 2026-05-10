from __future__ import annotations

import os
import subprocess
import sys


def validate_positive_integer(value: str, label: str) -> int:
    """Validate that *value* is a positive integer string.

    Returns 0 on success, 2 on failure (writes to stderr).
    """
    if not value or not value.isdigit() or value == "0":
        print(f"{label} must be a positive integer: {value}", file=sys.stderr)
        return 2
    return 0


def resolve_submodule_jobs(requested_jobs: str) -> str:
    """Return the number of parallel jobs to use for submodule operations.

    Priority order:
    1. *requested_jobs* (if non-empty)
    2. git config submodule.fetchJobs
    3. CPU count via os.cpu_count()
    4. Empty string (let git choose)
    """
    if requested_jobs:
        return requested_jobs

    proc = subprocess.run(
        ["git", "config", "--get", "submodule.fetchJobs"],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode == 0:
        configured = proc.stdout.strip()
        if configured:
            return configured

    cpu_count = os.cpu_count()
    if cpu_count is not None:
        return str(cpu_count)

    return ""


def run_submodule_update(
    no_fetch: bool,
    jobs: str,
    force: bool,
) -> int:
    """Run ``git submodule update --init`` with the given options.

    Returns the subprocess exit code.
    """
    cmd = [
        "git",
        "-c",
        "protocol.file.allow=always",
        "submodule",
        "update",
        "--init",
        "--recursive",
        "--recommend-shallow",
    ]
    if force:
        cmd.append("--force")
    if no_fetch:
        cmd.append("--no-fetch")
    if jobs:
        cmd.extend(["--jobs", jobs])
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def set_submodule_ignore_all() -> int:
    """Set ``ignore = all`` for every submodule in ``.gitmodules``.

    Mirrors the shell ``set_submodule_ignore_value all`` (no repo_input).
    Returns 0 on success, non-zero on failure.
    """
    proc = subprocess.run(
        [
            "git",
            "config",
            "-f",
            ".gitmodules",
            "--name-only",
            "--get-regexp",
            r"^submodule\..*\.path$",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        # No submodules - treat as success (same as shell behaviour)
        return 0

    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # strip .path suffix: "submodule.foo/bar.path" -> "submodule.foo/bar"
        section = line.removesuffix(".path")
        set_proc = subprocess.run(
            ["git", "config", "--local", f"{section}.ignore", "all"],
            check=False,
        )
        if set_proc.returncode != 0:
            return set_proc.returncode
    return 0


def set_submodule_ignore_value(repo_dir: str, value: str) -> int:
    """Set ``ignore = <value>`` for a single submodule in the local git config.

    *repo_dir* is the submodule path as recorded in ``.gitmodules``
    (e.g. ``repo/github.com/owner/name``).
    Returns 0 on success, non-zero on failure.
    """
    section = f"submodule.{repo_dir}"
    proc = subprocess.run(
        ["git", "config", "--local", f"{section}.ignore", value],
        check=False,
    )
    return proc.returncode
