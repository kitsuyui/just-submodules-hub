from __future__ import annotations

from pathlib import Path

import pytest

from just_submodules_hub.openers import opener_command


def test_opener_command_for_codex() -> None:
    repo = Path("/tmp/example")
    assert opener_command("codex", repo) == ["open", "-a", "Codex", str(repo)]


def test_opener_command_for_vscode_aliases() -> None:
    repo = Path("/tmp/example")
    assert opener_command("vscode", repo) == ["code", str(repo)]
    assert opener_command("code", repo) == ["code", str(repo)]
    assert opener_command("vs-code", repo) == ["code", str(repo)]


def test_opener_command_for_iterm_aliases() -> None:
    repo = Path("/tmp/example")
    assert opener_command("iterm2", repo) == ["open", "-a", "iTerm", str(repo)]
    assert opener_command("iterm", repo) == ["open", "-a", "iTerm", str(repo)]


def test_opener_command_rejects_unknown_tool() -> None:
    with pytest.raises(ValueError, match="unsupported tool"):
        opener_command("unknown", Path("/tmp/example"))
