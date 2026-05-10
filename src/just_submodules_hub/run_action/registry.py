from __future__ import annotations

import sys
from collections.abc import Callable

ActionFn = Callable[[list[str]], int]
_REGISTRY: dict[str, ActionFn] = {}


def action(name: str) -> Callable[[ActionFn], ActionFn]:
    """Register a callable as the handler for the named action."""

    def decorator(fn: ActionFn) -> ActionFn:
        if name in _REGISTRY:
            raise RuntimeError(f"action already registered: {name}")
        _REGISTRY[name] = fn
        return fn

    return decorator


def dispatch(name: str, args: list[str]) -> int:
    if name not in _REGISTRY:
        print(f"unknown action: {name}", file=sys.stderr)
        return 2
    return _REGISTRY[name](args)


def registered_actions() -> list[str]:
    return sorted(_REGISTRY.keys())
