"""Helpers for running GitHub CLI commands with bounded waits."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
from pathlib import Path

GH_COMMAND_TIMEOUT_SECONDS = 60.0
GH_COMMAND_TIMEOUT_RETURN_CODE = 124


def _format_seconds(timeout: float | None) -> str:
    seconds = GH_COMMAND_TIMEOUT_SECONDS if timeout is None else timeout
    return f"{seconds:g}"


def _timeout_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(errors="replace")
    return value


def run_gh(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run ``gh`` with a timeout and return a CompletedProcess-like result."""
    cmd = ["gh", *args]
    try:
        return subprocess.run(
            cmd,
            cwd=str(cwd) if cwd else None,
            text=True,
            capture_output=True,
            check=False,
            timeout=GH_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(
            cmd,
            GH_COMMAND_TIMEOUT_RETURN_CODE,
            stdout=_timeout_output(exc.stdout),
            stderr=(
                _timeout_output(exc.stderr)
                or f"gh command timed out after {_format_seconds(exc.timeout)} seconds"
            ),
        )
