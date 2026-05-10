from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from just_submodules_hub.default_heads import DefaultHead


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = PROJECT_ROOT / "scripts/repo/reconcile_submodule_worktrees.py"

spec = importlib.util.spec_from_file_location(
    "reconcile_submodule_worktrees", SCRIPT_PATH
)
assert spec is not None
reconcile = importlib.util.module_from_spec(spec)
sys.modules["reconcile_submodule_worktrees"] = reconcile
assert spec.loader is not None
spec.loader.exec_module(reconcile)


class DummyBar:
    def __init__(self) -> None:
        self.updated = 0

    def update(self, amount: int = 1) -> None:
        self.updated += amount


def test_build_reconcile_targets_prefilters_up_to_date_default_branch(
    monkeypatch, tmp_path
) -> None:
    bar = DummyBar()
    paths = [
        "repo/github.com/kitsuyui/up-to-date",
        "repo/github.com/kitsuyui/needs-work",
    ]

    monkeypatch.setattr(
        "just_submodules_hub.default_heads.fetch_default_heads_for_paths",
        lambda _paths, _bar: {
            "kitsuyui/up-to-date": DefaultHead("main", "aaa"),
            "kitsuyui/needs-work": DefaultHead("main", "bbb"),
        },
    )
    monkeypatch.setattr(
        "just_submodules_hub.default_heads.local_head",
        lambda repo_path: (
            ("main", "aaa")
            if str(repo_path).endswith("up-to-date")
            else ("main", "ccc")
        ),
    )
    monkeypatch.setattr(reconcile, "dirty_state", lambda repo: "clean")

    targets, results = reconcile.build_reconcile_targets(
        tmp_path, paths, prefilter=True, bar=bar
    )

    assert targets == ["repo/github.com/kitsuyui/needs-work"]
    assert results == [
        reconcile.Result(
            "repo/github.com/kitsuyui/up-to-date",
            "noop",
            "prefilter-default",
            "main",
            "",
            "clean",
            "already up to date",
        )
    ]
    assert bar.updated == 1


def test_build_reconcile_targets_keeps_root_repository(monkeypatch, tmp_path) -> None:
    bar = DummyBar()
    monkeypatch.setattr(
        "just_submodules_hub.default_heads.fetch_default_heads_for_paths",
        lambda _paths, _bar: {},
    )

    targets, results = reconcile.build_reconcile_targets(
        tmp_path, ["."], prefilter=True, bar=bar
    )

    assert targets == ["."]
    assert results == []
