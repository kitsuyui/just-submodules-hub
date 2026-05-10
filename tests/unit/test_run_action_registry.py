from __future__ import annotations

from collections.abc import Generator

import pytest

from just_submodules_hub.run_action import registry as reg


@pytest.fixture
def isolated_registry() -> Generator[None]:
    """Provide an isolated empty registry, restoring original state after the test."""
    saved = dict(reg._REGISTRY)
    reg._REGISTRY.clear()
    yield
    reg._REGISTRY.clear()
    reg._REGISTRY.update(saved)


def test_action_decorator_registers_function(isolated_registry: None) -> None:
    @reg.action("test-action")
    def handler(args: list[str]) -> int:
        return 0

    assert "test-action" in reg._REGISTRY
    assert reg._REGISTRY["test-action"] is handler


def test_action_decorator_raises_on_duplicate(isolated_registry: None) -> None:
    @reg.action("dup-action")
    def first(args: list[str]) -> int:
        return 0

    with pytest.raises(RuntimeError, match="action already registered: dup-action"):

        @reg.action("dup-action")
        def second(args: list[str]) -> int:
            return 1


def test_dispatch_calls_registered_function(isolated_registry: None) -> None:
    results: list[list[str]] = []

    @reg.action("my-action")
    def handler(args: list[str]) -> int:
        results.append(args)
        return 42

    rc = reg.dispatch("my-action", ["foo", "bar"])
    assert rc == 42
    assert results == [["foo", "bar"]]


def test_dispatch_returns_2_and_prints_stderr_for_unknown(
    isolated_registry: None,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = reg.dispatch("no-such-action", [])
    assert rc == 2
    captured = capsys.readouterr()
    assert "unknown action: no-such-action" in captured.err


def test_registered_actions_returns_sorted_list(isolated_registry: None) -> None:
    @reg.action("beta")
    def b(args: list[str]) -> int:
        return 0

    @reg.action("alpha")
    def a(args: list[str]) -> int:
        return 0

    assert reg.registered_actions() == ["alpha", "beta"]
