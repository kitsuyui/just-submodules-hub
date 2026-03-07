from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path

from .repo_paths import repo_display_name, repo_owner


def parse_gitmodules_paths(text: str) -> list[str]:
    parser = ConfigParser(interpolation=None)
    parser.read_string(text)

    paths: list[str] = []
    for section in parser.sections():
        if not section.startswith("submodule "):
            continue
        path = parser.get(section, "path", fallback="").strip()
        if path:
            paths.append(path)
    return paths


def read_gitmodules_paths(repo_root: Path | str = ".") -> list[str]:
    root = Path(repo_root)
    gitmodules_path = root / ".gitmodules"
    if not gitmodules_path.exists():
        return []
    return parse_gitmodules_paths(gitmodules_path.read_text(encoding="utf-8"))


def managed_repo_slugs(paths: list[str]) -> list[str]:
    return sorted({repo_display_name(path) for path in paths})


def managed_repo_owners(paths: list[str]) -> list[str]:
    return sorted({repo_owner(path) for path in paths})


def find_submodules_with_marker(marker_file: str, repo_root: Path | str = ".") -> list[str]:
    if not marker_file:
        raise ValueError("marker file is required")

    root = Path(repo_root)
    matches: list[str] = []
    for path in read_gitmodules_paths(root):
        if any((root / path).rglob(marker_file)):
            matches.append(path)
    return matches
