"""CLI entry point that dispatches to registered action handlers."""

from __future__ import annotations

import sys

from just_submodules_hub.run_action import (
    actions,  # noqa: F401  (side-effect: register actions)
)
from just_submodules_hub.run_action.registry import dispatch


def main(argv: list[str]) -> int:
    """Parse *argv*, dispatch to the named action, and return its exit code."""
    if not argv:
        print(
            "usage: python -m just_submodules_hub.run_action <action> [args...]",
            file=sys.stderr,
        )
        return 2
    action_name = argv[0]
    rest = argv[1:]
    return dispatch(action_name, rest)
