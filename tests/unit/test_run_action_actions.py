from __future__ import annotations

from pathlib import Path
from subprocess import CompletedProcess
from typing import Any

import pytest

# Import side-effect: register all actions into _REGISTRY
import just_submodules_hub.run_action.actions  # noqa: F401
import just_submodules_hub.run_action.actions.add_repo as add_repo_module
import just_submodules_hub.run_action.actions.cleanup_branches as cleanup_branches_module
import just_submodules_hub.run_action.actions.commit_submodule_pointers as commit_submodule_pointers_module
import just_submodules_hub.run_action.actions.create_repo as create_repo_module
import just_submodules_hub.run_action.actions.every_repo as every_repo_module
import just_submodules_hub.run_action.actions.grep as grep_module
import just_submodules_hub.run_action.actions.init_all_repos as init_all_repos_module
import just_submodules_hub.run_action.actions.linked_worktree_sync as linked_worktree_sync_module
import just_submodules_hub.run_action.actions.linked_worktrees as linked_worktrees_module
import just_submodules_hub.run_action.actions.list_github_repos as list_github_repos_module
import just_submodules_hub.run_action.actions.list_managed_repos as list_managed_repos_module
import just_submodules_hub.run_action.actions.list_unmanaged_repos as list_unmanaged_repos_module
import just_submodules_hub.run_action.actions.open_repo as open_repo_module
import just_submodules_hub.run_action.actions.reconcile_worktrees as reconcile_worktrees_module
import just_submodules_hub.run_action.actions.remove_repo as remove_repo_module
import just_submodules_hub.run_action.actions.sync_repo_default_branch as sync_repo_default_branch_module
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
    calls: list[tuple[str, str, Path]] = []

    def fake_open_repo_in_tool(tool: str, repo: str, hub_root: Path) -> None:
        calls.append((tool, repo, hub_root))

    monkeypatch.setattr(open_repo_module, "open_repo_in_tool", fake_open_repo_in_tool)
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
    def raise_error(tool: str, repo: str, hub_root: Path) -> None:
        raise ValueError("unsupported tool: bad")

    monkeypatch.setattr(open_repo_module, "open_repo_in_tool", raise_error)
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
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(every_repo_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["every-repo"]
    rc = fn(["ls", "--jobs", "2"])
    assert rc == 0
    assert calls[0][-3:] == ["ls", "--jobs", "2"]


# ---------- grep ----------


def test_grep_calls_git_grep(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(grep_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["grep"]
    rc = fn(["hello"])
    assert rc == 0
    assert calls == [["git", "grep", "--recurse-submodules", "hello"]]


def test_grep_passes_through_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        grep_module.subprocess,
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
    monkeypatch.setattr(
        list_github_repos_module,
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
    calls: list[tuple[str, str]] = []

    def fake_list(owner: str, vis: str) -> list[str]:
        calls.append((owner, vis))
        return []

    monkeypatch.setattr(list_github_repos_module, "_list_repos_for_owner", fake_list)
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
    def fake_list(owner: str, vis: str) -> list[str]:
        return [f"{owner}/shared\thttps://github.com/{owner}/shared"]

    monkeypatch.setattr(list_github_repos_module, "_list_repos_for_owner", fake_list)

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
    seen_owners: list[str] = []

    def fake_list(owner: str, vis: str) -> list[str]:
        seen_owners.append(owner)
        return []

    monkeypatch.setattr(list_github_repos_module, "_list_repos_for_owner", fake_list)

    fn = reg._REGISTRY["list-github-repos"]
    fn(["a,b,c", "all"])
    assert seen_owners == ["a", "b", "c"]


# ---------- list-managed-repos ----------


def test_list_managed_repos_no_args_prints_all(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        list_managed_repos_module,
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
    monkeypatch.setattr(
        list_managed_repos_module,
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
    monkeypatch.setattr(
        list_github_repos_module,
        "_list_repos_for_owner",
        lambda owner, vis: [
            "owner/managed\thttps://github.com/owner/managed",
            "owner/unmanaged\thttps://github.com/owner/unmanaged",
        ],
    )
    monkeypatch.setattr(
        list_unmanaged_repos_module,
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


# ---------- init-all-repos ----------


def test_init_all_repos_unknown_flag(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["init-all-repos"]
    rc = fn(["--unknown"])
    assert rc == 2
    assert "unknown init-all option" in capsys.readouterr().err


def test_init_all_repos_jobs_missing_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["init-all-repos"]
    rc = fn(["--jobs"])
    assert rc == 2
    assert "--jobs requires a value" in capsys.readouterr().err


def test_init_all_repos_delegates_to_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, ...]] = []

    def fake_resolve(requested: str) -> str:
        calls.append(("resolve", requested))
        return requested

    def fake_run(no_fetch: bool, jobs: str, force: bool) -> int:
        calls.append(("run", str(no_fetch), jobs, str(force)))
        return 0

    def fake_ignore() -> int:
        calls.append(("ignore",))
        return 0

    monkeypatch.setattr(init_all_repos_module, "resolve_submodule_jobs", fake_resolve)
    monkeypatch.setattr(init_all_repos_module, "run_submodule_update", fake_run)
    monkeypatch.setattr(init_all_repos_module, "set_submodule_ignore_all", fake_ignore)

    fn = reg._REGISTRY["init-all-repos"]
    rc = fn(["--no-fetch", "--jobs=4"])
    assert rc == 0
    assert ("run", "True", "4", "False") in calls
    assert ("ignore",) in calls


def test_init_all_repos_fetch_fallback_retries(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    run_calls: list[tuple[bool, str, bool]] = []

    def fake_resolve(requested: str) -> str:
        return requested

    def fake_run(no_fetch: bool, jobs: str, force: bool) -> int:
        run_calls.append((no_fetch, jobs, force))
        # First call (no-fetch) fails, second succeeds
        return 1 if no_fetch else 0

    def fake_ignore() -> int:
        return 0

    monkeypatch.setattr(init_all_repos_module, "resolve_submodule_jobs", fake_resolve)
    monkeypatch.setattr(init_all_repos_module, "run_submodule_update", fake_run)
    monkeypatch.setattr(init_all_repos_module, "set_submodule_ignore_all", fake_ignore)

    fn = reg._REGISTRY["init-all-repos"]
    rc = fn(["--fetch-fallback", "--jobs=2"])
    assert rc == 0
    assert len(run_calls) == 2
    assert run_calls[0] == (True, "2", False)
    assert run_calls[1] == (False, "2", False)
    assert "retrying with normal fetch" in capsys.readouterr().err


# ---------- sync-repo-default-branch / sync-all-repo-default-branch ----------


def test_sync_repo_default_branch_delegates_to_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Any] = []

    def fake_handle_one(args: Any) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(
        sync_repo_default_branch_module,
        "handle_one_action",
        fake_handle_one,
    )

    fn = reg._REGISTRY["sync-repo-default-branch"]
    rc = fn(["owner/repo"])
    assert rc == 0
    assert len(calls) == 1
    assert calls[0].repo_path == "owner/repo"


def test_sync_all_repo_default_branch_delegates_to_sync(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[Any] = []

    def fake_handle_all(args: Any) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(
        sync_repo_default_branch_module,
        "handle_all_action",
        fake_handle_all,
    )

    fn = reg._REGISTRY["sync-all-repo-default-branch"]
    rc = fn([])
    assert rc == 0
    assert len(calls) == 1


# ---------- reconcile-* ----------


def test_reconcile_submodule_worktree_requires_repo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["reconcile-submodule-worktree"]
    rc = fn([])
    assert rc == 2
    assert "REPO is required" in capsys.readouterr().err


def test_reconcile_submodule_worktree_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(reconcile_worktrees_module, "reconcile_main", fake_main)

    fn = reg._REGISTRY["reconcile-submodule-worktree"]
    rc = fn(["owner/repo", "--format", "tsv"])
    assert rc == 0
    assert calls[0][:3] == ["one", "owner/repo", "--format"]


def test_reconcile_submodule_worktrees_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(reconcile_worktrees_module, "reconcile_main", fake_main)

    fn = reg._REGISTRY["reconcile-submodule-worktrees"]
    rc = fn([])
    assert rc == 0
    assert calls[0][0] == "all"


def test_reconcile_worktrees_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(reconcile_worktrees_module, "reconcile_main", fake_main)

    fn = reg._REGISTRY["reconcile-worktrees"]
    rc = fn([])
    assert rc == 0
    assert calls[0][0] == "root-and-all"


# ---------- cleanup-* ----------


def test_cleanup_branches_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(cleanup_branches_module, "cleanup_main", fake_main)

    fn = reg._REGISTRY["cleanup-branches"]
    rc = fn(["--apply"])
    assert rc == 0
    assert calls[0][0] == "one"
    assert "--apply" in calls[0]


def test_cleanup_submodule_branches_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(cleanup_branches_module, "cleanup_main", fake_main)

    fn = reg._REGISTRY["cleanup-submodule-branches"]
    rc = fn([])
    assert rc == 0
    assert calls[0][0] == "all"


def test_cleanup_worktree_branches_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(cleanup_branches_module, "cleanup_main", fake_main)

    fn = reg._REGISTRY["cleanup-worktree-branches"]
    rc = fn([])
    assert rc == 0
    assert calls[0][0] == "root-and-all"


# ---------- add-repo ----------


def test_add_repo_requires_repo_url(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["add-repo"]
    rc = fn([])
    assert rc == 2
    assert "REPO_URL is required" in capsys.readouterr().err


def test_add_repo_calls_git_submodule_add(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(add_repo_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["add-repo"]
    rc = fn(["https://github.com/owner/myrepo"])
    assert rc == 0
    # First call: git submodule add
    assert calls[0] == [
        "git",
        "submodule",
        "add",
        "--",
        "git@github.com:owner/myrepo.git",
        "repo/github.com/owner/myrepo",
    ]
    # Second call: git config shallow
    assert "submodule.repo/github.com/owner/myrepo.shallow" in calls[1]
    # Third call: git config ignore all
    assert "submodule.repo/github.com/owner/myrepo.ignore" in calls[2]
    assert "all" in calls[2]


def test_add_repo_accepts_ssh_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(add_repo_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["add-repo"]
    rc = fn(["git@github.com:owner/myrepo.git"])
    assert rc == 0
    assert calls[0][4] == "git@github.com:owner/myrepo.git"
    assert calls[0][5] == "repo/github.com/owner/myrepo"


# ---------- remove-repo ----------


def test_remove_repo_requires_repo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["remove-repo"]
    rc = fn([])
    assert rc == 2
    assert "REPO is required" in capsys.readouterr().err


def test_remove_repo_calls_deinit_rm_git_rm(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(remove_repo_module.subprocess, "run", fake_run)
    monkeypatch.chdir(tmp_path)
    # Create a fake .gitmodules so resolve_repo_input can find "owner/myrepo"
    (tmp_path / ".gitmodules").write_text(
        '[submodule "repo/github.com/owner/myrepo"]\n'
        "\tpath = repo/github.com/owner/myrepo\n"
        "\turl = git@github.com:owner/myrepo.git\n",
        encoding="utf-8",
    )

    fn = reg._REGISTRY["remove-repo"]
    rc = fn(["owner/myrepo"])
    assert rc == 0
    assert [
        "git",
        "submodule",
        "deinit",
        "-f",
        "--",
        "repo/github.com/owner/myrepo",
    ] in calls
    assert ["git", "rm", "-f", "repo/github.com/owner/myrepo"] in calls


# ---------- commit-submodule-pointers ----------


def test_commit_submodule_pointers_no_changes(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        commit_submodule_pointers_module,
        "read_gitmodules_paths",
        lambda: ["repo/github.com/owner/repo"],
    )
    monkeypatch.setattr(
        commit_submodule_pointers_module,
        "_submodule_pointer_changed",
        lambda p: False,
    )

    fn = reg._REGISTRY["commit-submodule-pointers"]
    rc = fn([])
    assert rc == 0
    assert "No submodule pointer changes" in capsys.readouterr().out


def test_commit_submodule_pointers_commits_changed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        # diff --cached returns non-zero (changes staged)
        if "--quiet" in cmd:
            return CompletedProcess(cmd, 1)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(
        commit_submodule_pointers_module,
        "read_gitmodules_paths",
        lambda: ["repo/github.com/owner/repo"],
    )
    monkeypatch.setattr(
        commit_submodule_pointers_module,
        "_submodule_pointer_changed",
        lambda p: True,
    )
    monkeypatch.setattr(commit_submodule_pointers_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["commit-submodule-pointers"]
    rc = fn(["My commit message"])
    assert rc == 0
    # git add was called
    assert any("add" in c for c in calls)
    # git commit with correct message
    commit_calls = [c for c in calls if "commit" in c]
    assert commit_calls
    assert "My commit message" in commit_calls[0]


# ---------- list/plan/apply-linked-worktree-sync ----------


def test_list_linked_worktrees_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktree_sync_module, "list_main", fake_main)

    fn = reg._REGISTRY["list-linked-worktrees"]
    rc = fn(["--format", "jsonl"])
    assert rc == 0
    assert calls[0] == ["--format", "jsonl"]


def test_plan_linked_worktree_sync_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktree_sync_module, "plan_main", fake_main)

    fn = reg._REGISTRY["plan-linked-worktree-sync"]
    rc = fn([])
    assert rc == 0
    assert calls[0] == []


def test_apply_linked_worktree_sync_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktree_sync_module, "apply_main", fake_main)

    fn = reg._REGISTRY["apply-linked-worktree-sync"]
    rc = fn(["--from-plan-stdin"])
    assert rc == 0
    assert calls[0] == ["--from-plan-stdin"]


# ---------- create-public-repo / create-private-repo ----------


def test_create_public_repo_requires_repo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["create-public-repo"]
    rc = fn([])
    assert rc == 2
    assert "REPO is required" in capsys.readouterr().err


def test_create_private_repo_requires_repo(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["create-private-repo"]
    rc = fn([])
    assert rc == 2
    assert "REPO is required" in capsys.readouterr().err


def test_create_public_repo_creates_and_adds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # create_repo_module.subprocess is the same object as add_repo.subprocess (shared),
    # so we patch subprocess.run once and track all calls.
    all_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        all_calls.append(list(cmd))
        # gh repo view returns non-zero (repo not found)
        if len(cmd) > 2 and cmd[2] == "view":
            return CompletedProcess(cmd, 1)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(create_repo_module.subprocess, "run", fake_run)
    monkeypatch.setattr(create_repo_module.shutil, "which", lambda name: "/usr/bin/gh")

    fn = reg._REGISTRY["create-public-repo"]
    rc = fn(["owner/newrepo"])
    assert rc == 0
    # gh repo create --public was called
    create_calls = [c for c in all_calls if len(c) > 2 and c[2] == "create"]
    assert create_calls, f"No create call found in: {all_calls}"
    assert "--public" in create_calls[0]
    # git submodule add was called (add-repo dispatched internally)
    submodule_calls = [c for c in all_calls if "submodule" in c]
    assert submodule_calls


# ---------- install/reset/cleanup-linked-worktrees ----------


def test_install_linked_worktree_hooks_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktrees_module, "_safety_main", fake_main)

    fn = reg._REGISTRY["install-linked-worktree-hooks"]
    rc = fn(["--format", "tsv"])
    assert rc == 0
    assert calls[0][0] == "install-hooks"
    assert "--format" in calls[0]
    assert "tsv" in calls[0]


def test_reset_linked_worktree_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktrees_module, "_safety_main", fake_main)

    fn = reg._REGISTRY["reset-linked-worktree"]
    rc = fn(["/some/path", "--apply"])
    assert rc == 0
    assert calls[0][0] == "reset"
    assert "/some/path" in calls[0]
    assert "--apply" in calls[0]


def test_cleanup_linked_worktrees_delegates_to_main(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_main(argv: list[str] | None = None) -> int:
        calls.append(argv or [])
        return 0

    monkeypatch.setattr(linked_worktrees_module, "_safety_main", fake_main)

    fn = reg._REGISTRY["cleanup-linked-worktrees"]
    rc = fn(["--path-glob", "worktrees/*"])
    assert rc == 0
    assert calls[0][0] == "cleanup"
    assert "--path-glob" in calls[0]
    assert "worktrees/*" in calls[0]


def test_cleanup_linked_worktrees_passes_through_exit_code(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        linked_worktrees_module,
        "_safety_main",
        lambda argv=None: 1,
    )
    fn = reg._REGISTRY["cleanup-linked-worktrees"]
    rc = fn(["--path-glob", "*"])
    assert rc == 1


# ---------- remove-linked-worktree ----------


def test_remove_linked_worktree_requires_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["remove-linked-worktree"]
    rc = fn([])
    assert rc == 2
    assert "PATH is required" in capsys.readouterr().err


def test_remove_linked_worktree_calls_git_worktree_remove(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["remove-linked-worktree"]
    rc = fn(["/some/worktree"])
    assert rc == 0
    assert calls == [["git", "worktree", "remove", "/some/worktree"]]


def test_remove_linked_worktree_with_force(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        calls.append(cmd)
        return CompletedProcess(cmd, 0)

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)

    fn = reg._REGISTRY["remove-linked-worktree"]
    rc = fn(["/some/worktree", "--force"])
    assert rc == 0
    assert calls == [["git", "worktree", "remove", "--force", "/some/worktree"]]


def test_remove_linked_worktree_rejects_unknown_option(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        linked_worktrees_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 0),
    )
    fn = reg._REGISTRY["remove-linked-worktree"]
    rc = fn(["/some/worktree", "--unknown"])
    assert rc == 2
    assert "unknown linked worktree remove option" in capsys.readouterr().err


def test_remove_linked_worktree_rejects_extra_positional(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        linked_worktrees_module.subprocess,
        "run",
        lambda cmd, **kw: CompletedProcess(cmd, 0),
    )
    fn = reg._REGISTRY["remove-linked-worktree"]
    rc = fn(["/some/worktree", "extra-arg"])
    assert rc == 2
    assert "unexpected linked worktree remove argument" in capsys.readouterr().err


# ---------- add-linked-worktree ----------


def test_add_linked_worktree_requires_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([])
    assert rc == 2
    assert "PATH is required" in capsys.readouterr().err


def test_add_linked_worktree_basic(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git_calls: list[list[str]] = []
    dispatch_calls: list[tuple[str, list[str]]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        git_calls.append(cmd)
        return CompletedProcess(cmd, 0)

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatch_calls.append((name, args))
        return 0

    worktree_dir = tmp_path / "new-worktree"
    worktree_dir.mkdir()

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", fake_dispatch)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir)])
    assert rc == 0
    # git worktree add called without -b or start-point
    assert git_calls == [["git", "worktree", "add", str(worktree_dir)]]
    # init-all-repos dispatched with --force
    assert dispatch_calls == [("init-all-repos", ["--force"])]


def test_add_linked_worktree_with_branch_and_start_point(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git_calls: list[list[str]] = []
    dispatch_calls: list[tuple[str, list[str]]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        git_calls.append(cmd)
        return CompletedProcess(cmd, 0)

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatch_calls.append((name, args))
        return 0

    worktree_dir = tmp_path / "wt"
    worktree_dir.mkdir()

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", fake_dispatch)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir), "--branch", "feature/x", "origin/main"])
    assert rc == 0
    assert git_calls == [
        ["git", "worktree", "add", "-b", "feature/x", str(worktree_dir), "origin/main"],
    ]
    assert dispatch_calls[0][0] == "init-all-repos"
    assert "--force" in dispatch_calls[0][1]


def test_add_linked_worktree_no_submodules(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dispatch_calls: list[tuple[str, list[str]]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        return CompletedProcess(cmd, 0)

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatch_calls.append((name, args))
        return 0

    worktree_dir = tmp_path / "wt2"
    worktree_dir.mkdir()

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", fake_dispatch)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir), "--no-submodules"])
    assert rc == 0
    # dispatch should NOT be called when --no-submodules is given
    assert dispatch_calls == []


def test_add_linked_worktree_fetch_fallback_passed_to_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dispatch_calls: list[tuple[str, list[str]]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        return CompletedProcess(cmd, 0)

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatch_calls.append((name, args))
        return 0

    worktree_dir = tmp_path / "wt3"
    worktree_dir.mkdir()

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", fake_dispatch)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir), "--fetch-fallback", "--jobs=4"])
    assert rc == 0
    _, init_args = dispatch_calls[0]
    assert "--force" in init_args
    assert "--fetch-fallback" in init_args
    assert "--jobs" in init_args
    assert "4" in init_args


def test_add_linked_worktree_git_failure_skips_dispatch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    dispatch_calls: list[tuple[str, list[str]]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        return CompletedProcess(cmd, 128)

    def fake_dispatch(name: str, args: list[str]) -> int:
        dispatch_calls.append((name, args))
        return 0

    worktree_dir = tmp_path / "wt4"

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", fake_dispatch)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir)])
    assert rc == 128
    assert dispatch_calls == []


def test_add_linked_worktree_rejects_unknown_option(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn(["/some/path", "--unknown-flag"])
    assert rc == 2
    assert "unknown linked worktree add option" in capsys.readouterr().err


def test_add_linked_worktree_invalid_jobs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn(["/some/path", "--jobs=abc"])
    assert rc == 2
    assert "JOBS must be a positive integer" in capsys.readouterr().err


def test_add_linked_worktree_branch_short_form(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    git_calls: list[list[str]] = []

    def fake_run(cmd: list[str], **kwargs: Any) -> CompletedProcess[bytes]:
        git_calls.append(cmd)
        return CompletedProcess(cmd, 0)

    worktree_dir = tmp_path / "wt5"
    worktree_dir.mkdir()

    monkeypatch.setattr(linked_worktrees_module.subprocess, "run", fake_run)
    monkeypatch.setattr(linked_worktrees_module, "dispatch", lambda n, a: 0)

    fn = reg._REGISTRY["add-linked-worktree"]
    rc = fn([str(worktree_dir), "-b", "my-branch"])
    assert rc == 0
    assert git_calls[0] == [
        "git",
        "worktree",
        "add",
        "-b",
        "my-branch",
        str(worktree_dir),
    ]
