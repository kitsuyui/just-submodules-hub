#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.openers import open_repo_in_tool


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: open_repo.py <tool> <repo>", file=sys.stderr)
        return 2

    tool, repo = sys.argv[1], sys.argv[2]
    try:
        open_repo_in_tool(tool=tool, repo=repo, hub_root=Path.cwd())
    except (RuntimeError, ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
