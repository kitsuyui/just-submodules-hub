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


def clear_submodule_ignore_value(repo_dir: str) -> int:
    """Unset ``ignore`` for a single submodule in the local git config.

    *repo_dir* is the submodule path as recorded in ``.gitmodules``
    (e.g. ``repo/github.com/owner/name``).
    Silently succeeds if the key is not set, mirroring the shell behaviour
    (``git config --unset-all ... || true``).
    Returns 0 on success, non-zero on failure.
    """
    section = f"submodule.{repo_dir}"
    proc = subprocess.run(
        ["git", "config", "--local", "--unset-all", f"{section}.ignore"],
        check=False,
    )
    # exit code 5 means the key was not set; treat as success (same as shell)
    if proc.returncode in (0, 5):
        return 0
    return proc.returncode


def _iter_submodule_sections(repo_dir: str) -> list[tuple[str, str]]:
    """Return ``(section, path)`` pairs for submodules matching *repo_dir*.

    If *repo_dir* is non-empty, returns only the entry whose path equals
    *repo_dir*.  If empty, returns all submodule entries from ``.gitmodules``.
    This mirrors the shell ``target_submodule_sections`` helper.
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
        return []

    result: list[tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        section = line.removesuffix(".path")
        path_proc = subprocess.run(
            ["git", "config", "-f", ".gitmodules", "--get", f"{section}.path"],
            capture_output=True,
            text=True,
            check=False,
        )
        if path_proc.returncode != 0:
            continue
        path = path_proc.stdout.strip()
        if repo_dir and path != repo_dir:
            continue
        result.append((section, path))
    return result


def print_submodule_visibility_status(expected_value: str, repo_dir: str) -> int:
    r"""Print ``<path>\t(hidden|visible)`` for each matching submodule.

    For each submodule whose path matches *repo_dir* (or all submodules when
    *repo_dir* is empty), prints whether the ``ignore`` config key equals
    *expected_value*.  Mirrors ``print_submodule_visibility_status`` in the
    shell script.
    Returns 0 on success.
    """
    for section, path in _iter_submodule_sections(repo_dir):
        ignore_proc = subprocess.run(
            ["git", "config", "--local", "--get", f"{section}.ignore"],
            capture_output=True,
            text=True,
            check=False,
        )
        ignore_value = ignore_proc.stdout.strip() if ignore_proc.returncode == 0 else ""
        status = "hidden" if ignore_value == expected_value else "visible"
        print(f"{path}\t{status}")
    return 0


def print_submodule_ignore_raw_status(expected_value: str, repo_dir: str) -> int:
    r"""Print ``<path>\t(<value>|off)`` for each matching submodule.

    For each submodule whose path matches *repo_dir* (or all submodules when
    *repo_dir* is empty), prints the raw ignore value if it equals
    *expected_value*, otherwise prints ``off``.  Mirrors
    ``print_submodule_ignore_raw_status`` in the shell script.
    Returns 0 on success.
    """
    for section, path in _iter_submodule_sections(repo_dir):
        ignore_proc = subprocess.run(
            ["git", "config", "--local", "--get", f"{section}.ignore"],
            capture_output=True,
            text=True,
            check=False,
        )
        ignore_value = ignore_proc.stdout.strip() if ignore_proc.returncode == 0 else ""
        display = ignore_value if ignore_value == expected_value else "off"
        print(f"{path}\t{display}")
    return 0


def warn_deprecated_submodule_action(deprecated: str, canonical: str) -> None:
    """Write a deprecation warning to stderr.

    Mirrors ``warn_deprecated_submodule_action`` in the shell script:
    ``warning: <deprecated> is deprecated; use <canonical> instead``
    """
    sys.stderr.write(f"warning: {deprecated} is deprecated; use {canonical} instead\n")
