from __future__ import annotations

from subprocess import CompletedProcess
from typing import Any

import pytest

import just_submodules_hub.run_action.actions  # noqa: F401
import just_submodules_hub.run_action.actions._helpers as helpers_module
import just_submodules_hub.run_action.actions.submodule_deprecated_aliases as aliases_module
from just_submodules_hub.run_action import registry as reg

# ---------------------------------------------------------------------------
# Shared fake section list for stubs
# ---------------------------------------------------------------------------

_FAKE_SECTIONS = [("submodule.repo/github.com/owner/x", "repo/github.com/owner/x")]


# ---------------------------------------------------------------------------
# _helpers: clear_submodule_ignore_value
# ---------------------------------------------------------------------------


def test_clear_submodule_ignore_value_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(helpers_module.subprocess, "run", fake_run)
    rc = helpers_module.clear_submodule_ignore_value("repo/github.com/owner/myrepo")
    assert rc == 0
    assert calls == [
        [
            "git",
            "config",
            "--local",
            "--unset-all",
            "submodule.repo/github.com/owner/myrepo.ignore",
        ]
    ]


def test_clear_submodule_ignore_value_not_set_is_ok(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 5),
    )
    rc = helpers_module.clear_submodule_ignore_value("repo/github.com/owner/myrepo")
    assert rc == 0


def test_clear_submodule_ignore_value_other_error_propagates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 1),
    )
    rc = helpers_module.clear_submodule_ignore_value("repo/github.com/owner/myrepo")
    assert rc == 1


# ---------------------------------------------------------------------------
# _helpers: warn_deprecated_submodule_action
# ---------------------------------------------------------------------------


def test_warn_deprecated_submodule_action_writes_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    helpers_module.warn_deprecated_submodule_action("old-action", "new-action")
    err = capsys.readouterr().err
    assert "old-action" in err
    assert "new-action" in err
    assert "deprecated" in err


# ---------------------------------------------------------------------------
# _helpers: _iter_submodule_sections
# ---------------------------------------------------------------------------


def test_iter_submodule_sections_empty_when_no_gitmodules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 1),
    )
    result = helpers_module._iter_submodule_sections("")
    assert result == []


def test_iter_submodule_sections_filters_by_repo_dir(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[Any]:
        if "--get-regexp" in cmd:
            return CompletedProcess(
                cmd,
                0,
                stdout="submodule.repo/github.com/owner/a.path\nsubmodule.repo/github.com/owner/b.path\n",
            )
        if "submodule.repo/github.com/owner/a.path" in cmd:
            return CompletedProcess(cmd, 0, stdout="repo/github.com/owner/a\n")
        return CompletedProcess(cmd, 0, stdout="repo/github.com/owner/b\n")

    monkeypatch.setattr(helpers_module.subprocess, "run", fake_run)
    result = helpers_module._iter_submodule_sections("repo/github.com/owner/a")
    assert len(result) == 1
    assert result[0][1] == "repo/github.com/owner/a"


# ---------------------------------------------------------------------------
# _helpers: print_submodule_visibility_status
# ---------------------------------------------------------------------------


def test_print_submodule_visibility_status_hidden(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_dir: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 0, stdout="all\n"),
    )
    rc = helpers_module.print_submodule_visibility_status("all", "")
    assert rc == 0
    assert "hidden" in capsys.readouterr().out


def test_print_submodule_visibility_status_visible(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_dir: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 1, stdout=""),
    )
    rc = helpers_module.print_submodule_visibility_status("all", "")
    assert rc == 0
    assert "visible" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# _helpers: print_submodule_ignore_raw_status
# ---------------------------------------------------------------------------


def test_print_submodule_ignore_raw_status_matches(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_dir: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 0, stdout="dirty\n"),
    )
    rc = helpers_module.print_submodule_ignore_raw_status("dirty", "")
    assert rc == 0
    out = capsys.readouterr().out
    assert "dirty" in out
    assert "off" not in out


def test_print_submodule_ignore_raw_status_off(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_dir: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(
        helpers_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 1, stdout=""),
    )
    rc = helpers_module.print_submodule_ignore_raw_status("dirty", "")
    assert rc == 0
    assert "off" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# Live actions: submodule-root-status-hide/show/visibility
#
# Stub _helpers._iter_submodule_sections and _helpers.set/clear/print to
# verify the action dispatches correctly.
# ---------------------------------------------------------------------------


def test_submodule_root_status_hide_calls_set_ignore(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_set(path: str, value: str) -> int:
        calls.append((path, value))
        return 0

    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_filter: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(helpers_module, "set_submodule_ignore_value", fake_set)

    fn = reg._REGISTRY["submodule-root-status-hide"]
    rc = fn([])
    assert rc == 0
    assert calls == [("repo/github.com/owner/x", "all")]


def test_submodule_root_status_hide_with_repo_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filters_seen: list[str] = []

    def fake_iter(repo_filter: str) -> list[tuple[str, str]]:
        filters_seen.append(repo_filter)
        return _FAKE_SECTIONS

    monkeypatch.setattr(helpers_module, "_iter_submodule_sections", fake_iter)
    monkeypatch.setattr(
        helpers_module, "set_submodule_ignore_value", lambda path, value: 0
    )

    fn = reg._REGISTRY["submodule-root-status-hide"]
    rc = fn(["owner/myrepo"])
    assert rc == 0
    # normalize_repo_input converts owner/myrepo -> repo/github.com/owner/myrepo
    assert filters_seen == ["repo/github.com/owner/myrepo"]


def test_submodule_root_status_show_calls_clear(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []

    def fake_clear(path: str) -> int:
        calls.append(path)
        return 0

    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_filter: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(helpers_module, "clear_submodule_ignore_value", fake_clear)

    fn = reg._REGISTRY["submodule-root-status-show"]
    rc = fn([])
    assert rc == 0
    assert calls == ["repo/github.com/owner/x"]


def test_submodule_root_status_show_with_repo_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filters_seen: list[str] = []

    def fake_iter(repo_filter: str) -> list[tuple[str, str]]:
        filters_seen.append(repo_filter)
        return _FAKE_SECTIONS

    monkeypatch.setattr(helpers_module, "_iter_submodule_sections", fake_iter)
    monkeypatch.setattr(helpers_module, "clear_submodule_ignore_value", lambda path: 0)

    fn = reg._REGISTRY["submodule-root-status-show"]
    rc = fn(["owner/myrepo"])
    assert rc == 0
    assert filters_seen == ["repo/github.com/owner/myrepo"]


def test_submodule_root_status_visibility_calls_print(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_print(expected: str, repo: str) -> int:
        calls.append((expected, repo))
        return 0

    monkeypatch.setattr(helpers_module, "print_submodule_visibility_status", fake_print)

    fn = reg._REGISTRY["submodule-root-status-visibility"]
    rc = fn([])
    assert rc == 0
    assert calls == [("all", "")]


def test_submodule_root_status_visibility_with_repo_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_print(expected: str, repo: str) -> int:
        calls.append((expected, repo))
        return 0

    monkeypatch.setattr(helpers_module, "print_submodule_visibility_status", fake_print)
    fn = reg._REGISTRY["submodule-root-status-visibility"]
    rc = fn(["owner/myrepo"])
    assert rc == 0
    assert calls == [("all", "repo/github.com/owner/myrepo")]


# ---------------------------------------------------------------------------
# Deprecated aliases: warning + delegation
# ---------------------------------------------------------------------------


def _make_dispatch_spy(
    monkeypatch: pytest.MonkeyPatch,
) -> list[tuple[str, list[str]]]:
    dispatched: list[tuple[str, list[str]]] = []

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatched.append((name, args))
        return 0

    monkeypatch.setattr(aliases_module, "dispatch", fake_dispatch)
    return dispatched


@pytest.mark.parametrize(
    "alias",
    [
        "submodule-hide-root-status-changes",
        "submodule-hide-worktree-changes",
        "submodule-hide-all-changes",
        "submodule-ignore-all-on",
    ],
)
def test_hide_aliases_warn_and_dispatch_to_root_status_hide(
    alias: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dispatched = _make_dispatch_spy(monkeypatch)
    fn = reg._REGISTRY[alias]
    rc = fn(["owner/repo"])
    assert rc == 0
    assert dispatched == [("submodule-root-status-hide", ["owner/repo"])]
    err = capsys.readouterr().err
    assert "deprecated" in err
    assert alias in err


@pytest.mark.parametrize(
    "alias",
    [
        "submodule-show-root-status-changes",
        "submodule-show-worktree-changes",
        "submodule-show-all-changes",
        "submodule-ignore-all-off",
    ],
)
def test_show_aliases_warn_and_dispatch_to_root_status_show(
    alias: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dispatched = _make_dispatch_spy(monkeypatch)
    fn = reg._REGISTRY[alias]
    rc = fn([])
    assert rc == 0
    assert dispatched == [("submodule-root-status-show", [])]
    err = capsys.readouterr().err
    assert "deprecated" in err


@pytest.mark.parametrize(
    "alias",
    [
        "submodule-root-status-changes-visibility",
        "submodule-worktree-changes-visibility",
        "submodule-all-changes-visibility",
    ],
)
def test_visibility_aliases_warn_and_dispatch_to_root_status_visibility(
    alias: str,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dispatched = _make_dispatch_spy(monkeypatch)
    fn = reg._REGISTRY[alias]
    rc = fn([])
    assert rc == 0
    assert dispatched == [("submodule-root-status-visibility", [])]
    err = capsys.readouterr().err
    assert "deprecated" in err


# ---------------------------------------------------------------------------
# Dirty-specific deprecated actions
# ---------------------------------------------------------------------------


def test_submodule_ignore_dirty_on_warns_and_sets_dirty(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_set(path: str, value: str) -> int:
        calls.append((path, value))
        return 0

    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_filter: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(helpers_module, "set_submodule_ignore_value", fake_set)

    fn = reg._REGISTRY["submodule-ignore-dirty-on"]
    rc = fn([])
    assert rc == 0
    assert calls == [("repo/github.com/owner/x", "dirty")]
    err = capsys.readouterr().err
    assert "deprecated" in err
    assert "submodule-ignore-dirty-on" in err


def test_submodule_ignore_dirty_on_with_repo_arg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    filters_seen: list[str] = []

    def fake_iter(repo_filter: str) -> list[tuple[str, str]]:
        filters_seen.append(repo_filter)
        return _FAKE_SECTIONS

    monkeypatch.setattr(helpers_module, "_iter_submodule_sections", fake_iter)
    monkeypatch.setattr(
        helpers_module, "set_submodule_ignore_value", lambda path, value: 0
    )

    fn = reg._REGISTRY["submodule-ignore-dirty-on"]
    rc = fn(["owner/repo"])
    assert rc == 0
    assert filters_seen == ["repo/github.com/owner/repo"]


def test_submodule_ignore_dirty_off_warns_and_clears(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[str] = []

    def fake_clear(path: str) -> int:
        calls.append(path)
        return 0

    monkeypatch.setattr(
        helpers_module,
        "_iter_submodule_sections",
        lambda repo_filter: _FAKE_SECTIONS,
    )
    monkeypatch.setattr(helpers_module, "clear_submodule_ignore_value", fake_clear)

    fn = reg._REGISTRY["submodule-ignore-dirty-off"]
    rc = fn([])
    assert rc == 0
    assert calls == ["repo/github.com/owner/x"]
    err = capsys.readouterr().err
    assert "deprecated" in err


def test_submodule_ignore_dirty_status_warns_and_prints_raw(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_raw(expected: str, repo: str) -> int:
        calls.append((expected, repo))
        return 0

    monkeypatch.setattr(helpers_module, "print_submodule_ignore_raw_status", fake_raw)
    fn = reg._REGISTRY["submodule-ignore-dirty-status"]
    rc = fn(["owner/repo"])
    assert rc == 0
    # normalize_repo_input converts owner/repo -> repo/github.com/owner/repo
    assert calls == [("dirty", "repo/github.com/owner/repo")]
    err = capsys.readouterr().err
    assert "deprecated" in err


def test_submodule_ignore_all_status_warns_and_prints_raw(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[str, str]] = []

    def fake_raw(expected: str, repo: str) -> int:
        calls.append((expected, repo))
        return 0

    monkeypatch.setattr(helpers_module, "print_submodule_ignore_raw_status", fake_raw)
    fn = reg._REGISTRY["submodule-ignore-all-status"]
    rc = fn([])
    assert rc == 0
    assert calls == [("all", "")]
    err = capsys.readouterr().err
    assert "deprecated" in err
