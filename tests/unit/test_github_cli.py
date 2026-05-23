from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from just_submodules_hub.github_cli import (
    GH_COMMAND_TIMEOUT_RETURN_CODE,
    GH_COMMAND_TIMEOUT_SECONDS,
    run_gh,
)


def test_run_gh_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        captured["args"] = cmd
        captured["cwd"] = kwargs["cwd"]
        captured["timeout"] = kwargs["timeout"]
        return subprocess.CompletedProcess(cmd, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    proc = run_gh(["api", "user"], cwd=Path("/repo"))

    assert proc.stdout == "ok\n"
    assert captured["args"] == ["gh", "api", "user"]
    assert captured["cwd"] == "/repo"
    assert captured["timeout"] == GH_COMMAND_TIMEOUT_SECONDS


def test_run_gh_returns_timeout_process(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.TimeoutExpired(cmd, timeout=GH_COMMAND_TIMEOUT_SECONDS)

    monkeypatch.setattr(subprocess, "run", fake_run)

    proc = run_gh(["pr", "list"])

    assert proc.returncode == GH_COMMAND_TIMEOUT_RETURN_CODE
    assert "timed out after 60 seconds" in proc.stderr
