from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

# Import side-effect: register all actions into _REGISTRY
import just_submodules_hub.run_action.actions  # noqa: F401
from just_submodules_hub.run_action import registry as reg


# ---------- open-repo ----------


def test_open_repo_requires_tool_and_repo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["open-repo"]
    rc = fn([])
    assert rc == 2
    assert "TOOL and REPO are required" in capsys.readouterr().err


def test_open_repo_calls_open_repo_in_tool(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import just_submodules_hub.run_action.actions.open_repo as _mod

    calls: list[tuple[str, str, Path]] = []

    def fake_open_repo_in_tool(tool: str, repo: str, hub_root: Path) -> None:
        calls.append((tool, repo, hub_root))

    monkeypatch.setattr(_mod, "open_repo_in_tool", fake_open_repo_in_tool)
    monkeypatch.chdir(tmp_path)

    fn = reg._REGISTRY["open-repo"]
    rc = fn(["vscode", "owner/repo"])
    assert rc == 0
    assert calls == [("vscode", "owner/repo", tmp_path)]


def test_open_repo_returns_1_on_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.open_repo as _mod

    def raise_error(tool: str, repo: str, hub_root: Path) -> None:
        raise ValueError("unsupported tool: bad")

    monkeypatch.setattr(_mod, "open_repo_in_tool", raise_error)
    monkeypatch.chdir(tmp_path)

    fn = reg._REGISTRY["open-repo"]
    rc = fn(["bad", "owner/repo"])
    assert rc == 1
    assert "unsupported tool" in capsys.readouterr().err


# ---------- every-repo ----------


def test_every_repo_requires_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["every-repo"]
    rc = fn([])
    assert rc == 2
    assert "COMMAND is required" in capsys.readouterr().err


def test_every_repo_delegates_to_subprocess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import just_submodules_hub.run_action.actions.every_repo as _mod

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(_mod.subprocess, "run", fake_run)

    fn = reg._REGISTRY["every-repo"]
    rc = fn(["ls", "--jobs", "2"])
    assert rc == 0
    assert calls[0][-3:] == ["ls", "--jobs", "2"]


# ---------- grep ----------


def test_grep_calls_git_grep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import just_submodules_hub.run_action.actions.grep as _mod

    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(_mod.subprocess, "run", fake_run)

    fn = reg._REGISTRY["grep"]
    rc = fn(["hello"])
    assert rc == 0
    assert calls == [["git", "grep", "--recurse-submodules", "hello"]]


def test_grep_passes_through_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import just_submodules_hub.run_action.actions.grep as _mod

    monkeypatch.setattr(
        _mod.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 1),
    )

    fn = reg._REGISTRY["grep"]
    rc = fn(["no-match-pattern"])
    assert rc == 1


# ---------- list-github-repos-owner ----------


def test_list_github_repos_owner_requires_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["list-github-repos-owner"]
    rc = fn([])
    assert rc == 2
    assert "OWNER and VISIBILITY are required" in capsys.readouterr().err


def test_list_github_repos_owner_rejects_bad_visibility(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["list-github-repos-owner"]
    rc = fn(["owner", "bad-vis"])
    assert rc == 2
    assert "VISIBILITY must be one of" in capsys.readouterr().err


def test_list_github_repos_owner_prints_repos(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_github_repos as _mod

    monkeypatch.setattr(
        _mod,
        "_list_repos_for_owner",
        lambda owner, vis: ["owner/repo1\thttps://github.com/owner/repo1"],
    )
    fn = reg._REGISTRY["list-github-repos-owner"]
    rc = fn(["owner", "public"])
    assert rc == 0
    assert "owner/repo1" in capsys.readouterr().out


def test_list_github_repos_owner_all_visibility(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_github_repos as _mod

    calls: list[tuple[str, str]] = []

    def fake_list(owner: str, vis: str) -> list[str]:
        calls.append((owner, vis))
        return []

    monkeypatch.setattr(_mod, "_list_repos_for_owner", fake_list)
    fn = reg._REGISTRY["list-github-repos-owner"]
    fn(["owner", "all"])
    assert calls == [("owner", "all")]


# ---------- list-github-repos ----------


def test_list_github_repos_requires_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["list-github-repos"]
    rc = fn([])
    assert rc == 2
    assert "OWNERS and VISIBILITY are required" in capsys.readouterr().err


def test_list_github_repos_deduplicates_across_owners(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_github_repos as _mod

    def fake_list(owner: str, vis: str) -> list[str]:
        return [f"{owner}/shared\thttps://github.com/{owner}/shared"]

    monkeypatch.setattr(_mod, "_list_repos_for_owner", fake_list)

    fn = reg._REGISTRY["list-github-repos"]
    rc = fn(["ownerA,ownerB", "public"])
    assert rc == 0
    out = capsys.readouterr().out
    # ownerA/shared and ownerB/shared are different repos; both printed
    assert "ownerA/shared" in out
    assert "ownerB/shared" in out


def test_list_github_repos_comma_and_space_separated_owners(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_github_repos as _mod

    seen_owners: list[str] = []

    def fake_list(owner: str, vis: str) -> list[str]:
        seen_owners.append(owner)
        return []

    monkeypatch.setattr(_mod, "_list_repos_for_owner", fake_list)

    fn = reg._REGISTRY["list-github-repos"]
    fn(["a,b,c", "all"])
    assert seen_owners == ["a", "b", "c"]


# ---------- list-managed-repos ----------


def test_list_managed_repos_no_args_prints_all(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_managed_repos as _mod

    monkeypatch.setattr(
        _mod,
        "_get_managed_slugs",
        lambda cwd: ["owner/repo-b", "owner/repo-a"],
    )
    monkeypatch.chdir(tmp_path)

    fn = reg._REGISTRY["list-managed-repos"]
    rc = fn([])
    assert rc == 0
    assert capsys.readouterr().out.splitlines() == ["owner/repo-b", "owner/repo-a"]


def test_list_managed_repos_filters_by_owner(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_managed_repos as _mod

    monkeypatch.setattr(
        _mod,
        "_get_managed_slugs",
        lambda cwd: ["ownerA/repo1", "ownerB/repo2"],
    )
    monkeypatch.chdir(tmp_path)

    fn = reg._REGISTRY["list-managed-repos"]
    rc = fn(["ownerA", "all"])
    assert rc == 0
    assert capsys.readouterr().out.strip() == "ownerA/repo1"


def test_list_managed_repos_visibility_not_all_requires_owners(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    fn = reg._REGISTRY["list-managed-repos"]
    rc = fn(["", "public"])
    assert rc == 2
    assert "OWNERS is required" in capsys.readouterr().err


# ---------- list-unmanaged-repos ----------


def test_list_unmanaged_repos_requires_args(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["list-unmanaged-repos"]
    rc = fn([])
    assert rc == 2
    assert "OWNERS and VISIBILITY are required" in capsys.readouterr().err


def test_list_unmanaged_repos_prints_difference(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import just_submodules_hub.run_action.actions.list_github_repos as _lgh
    import just_submodules_hub.run_action.actions.list_unmanaged_repos as _mod

    monkeypatch.setattr(
        _lgh,
        "_list_repos_for_owner",
        lambda owner, vis: [
            "owner/managed\thttps://github.com/owner/managed",
            "owner/unmanaged\thttps://github.com/owner/unmanaged",
        ],
    )
    monkeypatch.setattr(
        _mod,
        "read_gitmodules_paths",
        lambda cwd: ["repo/github.com/owner/managed"],
    )
    monkeypatch.chdir(tmp_path)

    fn = reg._REGISTRY["list-unmanaged-repos"]
    rc = fn(["owner", "public"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "owner/unmanaged" in out
    assert "owner/managed" not in out
