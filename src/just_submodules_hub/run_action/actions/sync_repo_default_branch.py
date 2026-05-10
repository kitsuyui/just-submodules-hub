from __future__ import annotations

import sys

from just_submodules_hub.run_action.registry import action
from just_submodules_hub.sync import build_parser, handle_all_action, handle_one_action


@action("sync-repo-default-branch")
def sync_repo_default_branch(args: list[str]) -> int:
    # Equivalent to: sync_default_branch.py one <repo> [args...]
    parser = build_parser()
    try:
        parsed = parser.parse_args(["one", *args])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2
    try:
        return handle_one_action(parsed)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1


@action("sync-all-repo-default-branch")
def sync_all_repo_default_branch(args: list[str]) -> int:
    # Equivalent to: sync_default_branch.py all [args...]
    parser = build_parser()
    try:
        parsed = parser.parse_args(["all", *args])
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else 2
    try:
        return handle_all_action(parsed)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1
