from __future__ import annotations

from just_submodules_hub import sync


class DummyBar:
    def __init__(self) -> None:
        self.total = 0
        self.updated = 0

    def update(self, amount: int = 1) -> None:
        self.updated += amount

    def refresh(self) -> None:
        return None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_build_sync_targets_skips_up_to_date_repositories(monkeypatch) -> None:
    bar = DummyBar()

    monkeypatch.setattr(
        sync,
        "fetch_owner_default_heads",
        lambda owner, _bar: {
            "kitsuyui/ts-playground": ("main", "aaa"),
            "kitsuyui/react-playground": ("main", "bbb"),
        },
    )
    monkeypatch.setattr(
        sync,
        "local_head",
        lambda repo_path: ("main", "aaa")
        if repo_path.endswith("ts-playground")
        else ("main", "ccc"),
    )

    targets = sync.build_sync_targets(
        [
            "repo/github.com/kitsuyui/ts-playground",
            "repo/github.com/kitsuyui/react-playground",
        ],
        prefilter=True,
        bar=bar,
    )

    assert targets == ["repo/github.com/kitsuyui/react-playground"]
    assert bar.updated == 1


def test_extract_default_head_ignores_incomplete_nodes() -> None:
    assert sync.extract_default_head({"name": "sample-repo"}, "kitsuyui") is None


def test_should_sync_target_handles_missing_remote_head() -> None:
    assert sync.should_sync_target(None, "main", "abc")
    assert not sync.should_sync_target(("main", "abc"), "main", "abc")


def test_parse_head_branch_line_returns_none_when_missing() -> None:
    assert sync.parse_head_branch_line("origin\n  Fetch URL: example") is None
    assert sync.parse_head_branch_line("  HEAD branch: main\n") == "main"


def test_render_sync_result_variants() -> None:
    changed = sync.SyncResult(
        repo_path="repo/github.com/kitsuyui/sample-repo",
        default_branch="main",
        switched=True,
        updated=True,
    )
    assert sync.render_sync_result("kitsuyui/sample-repo", changed, verbose=False) == (
        "kitsuyui/sample-repo: switched-to:main updated-to:latest"
    )

    skipped = sync.SyncResult(
        repo_path="repo/github.com/kitsuyui/sample-repo",
        default_branch="DETACHED",
        switched=False,
        updated=False,
        skipped=True,
        skip_reason="dirty working tree",
    )
    assert sync.render_sync_result("kitsuyui/sample-repo", skipped, verbose=False) == (
        "kitsuyui/sample-repo: skipped (dirty working tree)"
    )

    unchanged = sync.SyncResult(
        repo_path="repo/github.com/kitsuyui/sample-repo",
        default_branch="main",
        switched=False,
        updated=False,
    )
    assert sync.render_sync_result("kitsuyui/sample-repo", unchanged, verbose=False) is None
    assert sync.render_sync_result("kitsuyui/sample-repo", unchanged, verbose=True) == "kitsuyui/sample-repo: up-to-date"


def test_owner_prefilter_total() -> None:
    paths = [
        "repo/github.com/kitsuyui/sample-repo",
        "repo/github.com/kitsuyui/other",
        "repo/github.com/gitignore-in/site",
    ]
    assert sync.owner_prefilter_total(paths, prefilter=True) == 2
    assert sync.owner_prefilter_total(paths, prefilter=False) == 0


def test_positive_int_rejects_invalid_values() -> None:
    assert sync.positive_int("3") == 3
    for value in ("0", "-1", "abc"):
        try:
            sync.positive_int(value)
        except Exception:
            pass
        else:
            raise AssertionError(f"positive_int should reject {value}")


def test_parse_repo_paths_reads_gitmodules(tmp_path) -> None:
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "repo/github.com/kitsuyui/sample-repo"]
    path = repo/github.com/kitsuyui/sample-repo
""".strip(),
        encoding="utf-8",
    )
    assert sync.parse_repo_paths(tmp_path) == ["repo/github.com/kitsuyui/sample-repo"]


def test_resolve_default_branch_prefers_symbolic_ref(monkeypatch) -> None:
    def fake_run(cmd, cwd=None):
        if cmd[:3] == ["git", "symbolic-ref", "--short"]:
            return "origin/main"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(sync, "run", fake_run)
    assert sync.resolve_default_branch("repo/github.com/kitsuyui/sample-repo") == "main"


def test_resolve_default_branch_falls_back_to_remote_show(monkeypatch) -> None:
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append(cmd)
        if cmd[:3] == ["git", "symbolic-ref", "--short"]:
            raise RuntimeError("missing")
        if cmd[:3] == ["git", "remote", "show"]:
            return "  HEAD branch: trunk\n"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(sync, "run", fake_run)
    assert sync.resolve_default_branch("repo/github.com/kitsuyui/sample-repo") == "trunk"


def test_main_reports_when_no_submodules(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync, "parse_repo_paths", lambda: [])
    monkeypatch.setattr(sync.argparse.ArgumentParser, "parse_args", lambda self: type("Args", (), {"action": "all", "prefilter": True, "jobs": 1, "verbose": False})())
    assert sync.main() == 0
    assert "No submodule paths found in .gitmodules" in capsys.readouterr().out


def test_fetch_owner_default_heads_handles_pagination(monkeypatch) -> None:
    bar = DummyBar()
    responses = iter(
        [
            {
                "data": {
                    "repositoryOwner": {
                        "repositories": {
                            "nodes": [{"name": "sample-repo", "defaultBranchRef": {"name": "main", "target": {"oid": "aaa"}}}],
                            "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                        }
                    }
                }
            },
            {
                "data": {
                    "repositoryOwner": {
                        "repositories": {
                            "nodes": [{"name": "sample-repo-2", "defaultBranchRef": {"name": "trunk", "target": {"oid": "bbb"}}}],
                            "pageInfo": {"hasNextPage": False, "endCursor": None},
                        }
                    }
                }
            },
        ]
    )
    monkeypatch.setattr(sync, "gh_graphql", lambda owner, cursor: next(responses))
    heads = sync.fetch_owner_default_heads("kitsuyui", bar)
    assert heads == {"kitsuyui/sample-repo": ("main", "aaa"), "kitsuyui/sample-repo-2": ("trunk", "bbb")}
    assert bar.updated == 2


def test_fetch_owner_default_heads_rejects_missing_owner(monkeypatch) -> None:
    bar = DummyBar()
    monkeypatch.setattr(sync, "gh_graphql", lambda owner, cursor: {"data": {"repositoryOwner": None}})
    try:
        sync.fetch_owner_default_heads("kitsuyui", bar)
    except RuntimeError as exc:
        assert str(exc) == "repository owner not found: kitsuyui"
    else:
        raise AssertionError("missing repository owner should raise")


def test_sync_all_reports_failures(monkeypatch, capsys) -> None:
    bar = DummyBar()

    def fake_sync_one(path: str):
        if path.endswith("bad"):
            raise RuntimeError("boom")
        return sync.SyncResult(repo_path=path, default_branch="main", switched=True, updated=False)

    monkeypatch.setattr(sync, "sync_one", fake_sync_one)
    code, changed_count = sync.sync_all(
        ["repo/github.com/kitsuyui/good", "repo/github.com/kitsuyui/bad"],
        jobs=2,
        verbose=False,
        bar=bar,
    )
    captured = capsys.readouterr()
    assert code == 1
    assert changed_count == 1
    assert "kitsuyui/bad: boom" in captured.err


def test_local_head_returns_detached_when_symbolic_ref_fails(monkeypatch) -> None:
    calls = []

    def fake_run(cmd, cwd=None):
        calls.append(cmd)
        if cmd[:3] == ["git", "symbolic-ref", "--quiet"]:
            raise RuntimeError("detached")
        if cmd[:2] == ["git", "rev-parse"]:
            return "abc123"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(sync, "run", fake_run)
    assert sync.local_head("repo/github.com/kitsuyui/sample-repo") == ("DETACHED", "abc123")


def test_sync_one_rejects_missing_repository(tmp_path) -> None:
    try:
        sync.sync_one(str(tmp_path / "missing"))
    except RuntimeError as exc:
        assert "Repository path not found" in str(exc)
    else:
        raise AssertionError("sync_one should reject missing repositories")


def test_sync_one_skips_dirty_repository(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir", encoding="utf-8")

    def fake_run(cmd, cwd=None):
        if cmd[:3] == ["git", "symbolic-ref", "--quiet"]:
            return "main"
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return " M README.md"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(sync, "run", fake_run)
    result = sync.sync_one(str(repo))
    assert result.skipped
    assert result.skip_reason == "dirty working tree"


def test_sync_one_switches_and_updates(monkeypatch, tmp_path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / ".git").write_text("gitdir", encoding="utf-8")
    state = {"head": "old", "branch": "feature"}

    def fake_run(cmd, cwd=None):
        if cmd[:3] == ["git", "symbolic-ref", "--quiet"]:
            return state["branch"]
        if cmd[:3] == ["git", "status", "--porcelain"]:
            return ""
        if cmd[:3] == ["git", "fetch", "origin"]:
            return ""
        if cmd[:3] == ["git", "symbolic-ref", "--short"]:
            return "origin/main"
        if cmd[:2] == ["git", "switch"]:
            state["branch"] = cmd[-1]
            return ""
        if cmd[:2] == ["git", "pull"]:
            state["head"] = "new"
            return ""
        if cmd[:2] == ["git", "rev-parse"]:
            return state["head"]
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(sync, "run", fake_run)
    result = sync.sync_one(str(repo))
    assert result.default_branch == "main"
    assert result.switched
    assert result.updated


def test_handle_one_action(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        sync,
        "sync_one",
        lambda repo_path: sync.SyncResult(repo_path=repo_path, default_branch="main", switched=False, updated=False),
    )
    monkeypatch.setattr(sync, "print_result", lambda result, verbose: calls.append((result.repo_path, verbose)) or False)
    args = type("Args", (), {"repo_path": "repo/github.com/kitsuyui/sample-repo", "verbose": True})()
    assert sync.handle_one_action(args) == 0
    assert calls == [("repo/github.com/kitsuyui/sample-repo", True)]


def test_handle_all_action_reports_all_up_to_date(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync, "parse_repo_paths", lambda: ["repo/github.com/kitsuyui/sample-repo"])
    monkeypatch.setattr(sync, "build_sync_targets", lambda paths, prefilter, bar: [])
    monkeypatch.setattr(sync, "tqdm", lambda **kwargs: DummyBar())
    args = type("Args", (), {"prefilter": True, "jobs": 1, "verbose": False})()
    assert sync.handle_all_action(args) == 0
    assert "All submodules are up to date." in capsys.readouterr().out


def test_handle_all_action_runs_sync_all(monkeypatch) -> None:
    monkeypatch.setattr(sync, "parse_repo_paths", lambda: ["repo/github.com/kitsuyui/sample-repo"])
    monkeypatch.setattr(sync, "build_sync_targets", lambda paths, prefilter, bar: list(paths))
    monkeypatch.setattr(sync, "sync_all", lambda paths, jobs, verbose, bar: (0, 1))
    monkeypatch.setattr(sync, "tqdm", lambda **kwargs: DummyBar())
    args = type("Args", (), {"prefilter": True, "jobs": 3, "verbose": False})()
    assert sync.handle_all_action(args) == 0


def test_handle_all_action_prints_when_sync_all_reports_no_changes(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync, "parse_repo_paths", lambda: ["repo/github.com/kitsuyui/sample-repo"])
    monkeypatch.setattr(sync, "build_sync_targets", lambda paths, prefilter, bar: list(paths))
    monkeypatch.setattr(sync, "sync_all", lambda paths, jobs, verbose, bar: (0, 0))
    monkeypatch.setattr(sync, "tqdm", lambda **kwargs: DummyBar())
    args = type("Args", (), {"prefilter": True, "jobs": 1, "verbose": False})()
    assert sync.handle_all_action(args) == 0
    assert "All submodules are up to date." in capsys.readouterr().out


def test_main_handles_runtime_error(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sync.argparse.ArgumentParser, "parse_args", lambda self: type("Args", (), {"action": "one", "repo_path": "repo/github.com/kitsuyui/sample-repo", "verbose": False})())
    monkeypatch.setattr(sync, "handle_one_action", lambda args: (_ for _ in ()).throw(RuntimeError("boom")))
    assert sync.main() == 1
    assert "boom" in capsys.readouterr().err
