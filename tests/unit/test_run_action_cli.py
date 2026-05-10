from __future__ import annotations

from collections.abc import Generator

import pytest

from just_submodules_hub.run_action import registry as reg
from just_submodules_hub.run_action.cli import main


@pytest.fixture
def isolated_registry() -> Generator[None]:
    """Provide a clean registry for tests that register fake actions."""
    saved = dict(reg._REGISTRY)
    reg._REGISTRY.clear()
    yield
    reg._REGISTRY.clear()
    reg._REGISTRY.update(saved)


def test_main_without_args_prints_usage_and_returns_2(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = main([])
    assert rc == 2
    captured = capsys.readouterr()
    assert "usage" in captured.err


def test_main_with_unknown_action_returns_2(
    capsys: pytest.CaptureFixture[str],
    isolated_registry: None,
) -> None:
    rc = main(["unknown-xyz"])
    assert rc == 2
    captured = capsys.readouterr()
    assert "unknown action" in captured.err


def test_main_dispatches_to_registered_action(
    isolated_registry: None,
) -> None:
    results: list[list[str]] = []

    @reg.action("fake-action")
    def handler(args: list[str]) -> int:
        results.append(args)
        return 7

    rc = main(["fake-action", "a", "b"])
    assert rc == 7
    assert results == [["a", "b"]]
