#!/usr/bin/env python3

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.repo_paths import resolve_repo_input


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: resolve_repo.py <repo>", file=sys.stderr)
        return 2

    try:
        print(resolve_repo_input(sys.argv[1], Path.cwd()))
    except (ValueError, FileNotFoundError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
