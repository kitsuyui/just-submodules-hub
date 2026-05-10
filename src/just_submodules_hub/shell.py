from __future__ import annotations

import shlex
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

SENSITIVE_ENV_PARTS = ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL", "AUTH")


def sensitive_values(env: Mapping[str, str] | None) -> list[str]:
    if env is None:
        return []
    return [
        value
        for key, value in env.items()
        if value and any(part in key.upper() for part in SENSITIVE_ENV_PARTS)
    ]


def redact(text: str, redactions: Sequence[str]) -> str:
    redacted = text
    for value in redactions:
        redacted = redacted.replace(value, "<redacted>")
    return redacted


def command_failure_message(
    cmd: Sequence[str],
    returncode: int,
    cwd: Path | None,
    output: str,
    redactions: Sequence[str],
) -> str:
    display_cwd = cwd if cwd else Path.cwd()
    details = [
        f"command failed: {redact(shlex.join(cmd), redactions)}",
        f"cwd: {display_cwd}",
        f"exit code: {returncode}",
    ]
    if output:
        details.append(f"output: {redact(output, redactions)}")
    return "\n".join(details)


def run(
    cmd: Sequence[str],
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
) -> str:
    redactions = sensitive_values(env)
    proc = subprocess.run(
        list(cmd),
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env else None,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        output = (proc.stderr or proc.stdout).strip()
        raise RuntimeError(
            command_failure_message(cmd, proc.returncode, cwd, output, redactions)
        )
    return proc.stdout.strip()
