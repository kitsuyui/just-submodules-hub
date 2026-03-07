#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from just_submodules_hub.gitmodules import find_submodules_with_marker


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="List submodules that contain a marker file")
    parser.add_argument("marker_file", help="marker file name such as pyproject.toml")
    parser.add_argument("--repo-root", default=".", help="repository root (default: current directory)")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    for path in find_submodules_with_marker(args.marker_file, repo_root=args.repo_root):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
