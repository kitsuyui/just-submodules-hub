from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess

import pytest

from just_submodules_hub import shell


def test_run_returns_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(
            args[0],
            0,
            stdout="hello\n",
            stderr="",
        ),
    )
    assert shell.run(["echo", "hello"]) == "hello"


def test_run_raises_runtime_error_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 1, stdout="", stderr="boom"),
    )
    with pytest.raises(RuntimeError) as excinfo:
        shell.run(["false"])

    message = str(excinfo.value)
    assert "command failed: false" in message
    assert "exit code: 1" in message
    assert "output: boom" in message


def test_run_raises_runtime_error_with_cwd(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(
            args[0],
            2,
            stdout="bad path",
            stderr="",
        ),
    )
    with pytest.raises(RuntimeError) as excinfo:
        shell.run(["git", "status"], cwd=tmp_path)

    message = str(excinfo.value)
    assert "command failed: git status" in message
    assert f"cwd: {tmp_path}" in message
    assert "exit code: 2" in message
    assert "output: bad path" in message


def test_run_redacts_sensitive_env_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(
            args[0],
            1,
            stdout="",
            stderr="failed with token secret-token",
        ),
    )
    with pytest.raises(RuntimeError) as excinfo:
        shell.run(
            ["gh", "api", "repos?token=secret-token"],
            env={"GITHUB_TOKEN": "secret-token"},
        )

    message = str(excinfo.value)
    assert "secret-token" not in message
    assert "<redacted>" in message


def test_run_passes_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], **kwargs: object) -> CompletedProcess[str]:
        captured["timeout"] = kwargs["timeout"]
        return CompletedProcess(cmd, 0, stdout="hello\n", stderr="")

    monkeypatch.setattr(shell.subprocess, "run", fake_run)

    assert shell.run(["echo", "hello"], timeout=12.5) == "hello"
    assert captured["timeout"] == 12.5


def test_run_raises_runtime_error_on_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **kwargs: object) -> CompletedProcess[str]:
        raise shell.subprocess.TimeoutExpired(cmd, timeout=12.5)

    monkeypatch.setattr(shell.subprocess, "run", fake_run)

    with pytest.raises(RuntimeError) as excinfo:
        shell.run(["gh", "api", "user"], timeout=12.5)

    message = str(excinfo.value)
    assert "command failed: gh api user" in message
    assert "exit code: 124" in message
    assert "timed out after 12.5 seconds" in message
