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
