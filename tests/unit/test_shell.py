from __future__ import annotations

from subprocess import CompletedProcess

import pytest

from just_submodules_hub import shell


def test_run_returns_stdout(monkeypatch) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 0, stdout="hello\n", stderr=""),
    )
    assert shell.run(["echo", "hello"]) == "hello"


def test_run_raises_runtime_error_on_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        shell.subprocess,
        "run",
        lambda *args, **kwargs: CompletedProcess(args[0], 1, stdout="", stderr="boom"),
    )
    with pytest.raises(RuntimeError, match="boom"):
        shell.run(["false"])
