from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import pytest

from just_submodules_hub import default_branch as db_module
from just_submodules_hub.default_branch import (
    parse_head_branch_line,
    resolve_default_branch,
)

# ---------------------------------------------------------------------------
# parse_head_branch_line
# ---------------------------------------------------------------------------


def test_parse_head_branch_line_returns_none_when_absent() -> None:
    assert parse_head_branch_line("  HEAD poll: whatever\n") is None


def test_parse_head_branch_line_detects_branch() -> None:
    output = "  Remote branches:\n    main tracked\n  HEAD branch: main\n"
    assert parse_head_branch_line(output) == "main"


def test_parse_head_branch_line_detects_non_main_branch() -> None:
    output = "  HEAD branch: trunk\n"
    assert parse_head_branch_line(output) == "trunk"


# ---------------------------------------------------------------------------
# resolve_default_branch - symbolic-ref path
# ---------------------------------------------------------------------------


def test_resolve_default_branch_prefers_symbolic_ref(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        if list(cmd)[:3] == ["git", "symbolic-ref", "--short"]:
            return "origin/main"
        raise AssertionError(f"unexpected: {list(cmd)}")

    monkeypatch.setattr(db_module, "run", fake_run)
    assert resolve_default_branch("/tmp/repo") == "main"


def test_resolve_default_branch_supports_custom_remote(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        if list(cmd)[:3] == ["git", "symbolic-ref", "--short"]:
            return "upstream/develop"
        raise AssertionError(f"unexpected: {list(cmd)}")

    monkeypatch.setattr(db_module, "run", fake_run)
    assert resolve_default_branch("/tmp/repo", remote="upstream") == "develop"


# ---------------------------------------------------------------------------
# resolve_default_branch - remote show fallback
# ---------------------------------------------------------------------------


def test_resolve_default_branch_falls_back_to_remote_show(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        calls.append(list(cmd))
        if list(cmd)[:3] == ["git", "symbolic-ref", "--short"]:
            raise RuntimeError("no symbolic-ref")
        if list(cmd)[:3] == ["git", "remote", "show"]:
            return "  HEAD branch: trunk\n"
        raise AssertionError(f"unexpected: {list(cmd)}")

    monkeypatch.setattr(db_module, "run", fake_run)
    assert resolve_default_branch("/tmp/repo") == "trunk"


# ---------------------------------------------------------------------------
# resolve_default_branch - fallback value
# ---------------------------------------------------------------------------


def test_resolve_default_branch_returns_fallback_when_both_fail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        raise RuntimeError("offline")

    monkeypatch.setattr(db_module, "run", fake_run)
    # Default fallback is "main"
    assert resolve_default_branch("/tmp/repo") == "main"


def test_resolve_default_branch_returns_custom_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        raise RuntimeError("offline")

    monkeypatch.setattr(db_module, "run", fake_run)
    assert resolve_default_branch("/tmp/repo", fallback="master") == "master"


def test_resolve_default_branch_raises_when_fallback_is_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: Sequence[str], cwd: Path | None = None) -> str:
        raise RuntimeError("offline")

    monkeypatch.setattr(db_module, "run", fake_run)
    with pytest.raises(RuntimeError, match="Could not resolve default branch"):
        resolve_default_branch("/tmp/repo", fallback=None)
