from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from .repo_paths import repo_display_name, repo_owner
from .submodule_filters import SubmoduleFilter


@dataclass(frozen=True)
class SubmoduleEntry:
    name: str
    path: str
    url: str


def parse_submodule_section_name(section: str) -> str:
    name = section.removeprefix("submodule ").strip()
    if len(name) >= 2 and name[0] == '"' and name[-1] == '"':
        return name[1:-1]
    return name


def parse_gitmodules_entries(text: str) -> list[SubmoduleEntry]:
    if not text.strip():
        return []
    parser = ConfigParser(interpolation=None)
    parser.read_string(text)

    entries: list[SubmoduleEntry] = []
    for section in parser.sections():
        if not section.startswith("submodule "):
            continue
        path = parser.get(section, "path", fallback="").strip()
        if not path:
            continue
        name = parse_submodule_section_name(section) or path
        url = parser.get(section, "url", fallback="").strip()
        entries.append(SubmoduleEntry(name=name, path=path, url=url))
    return entries


def parse_gitmodules_paths(text: str) -> list[str]:
    return [entry.path for entry in parse_gitmodules_entries(text)]


def read_gitmodules_paths(repo_root: Path | str = ".") -> list[str]:
    root = Path(repo_root)
    gitmodules_path = root / ".gitmodules"
    if not gitmodules_path.exists():
        return []
    return parse_gitmodules_paths(gitmodules_path.read_text(encoding="utf-8"))


def read_gitmodules_entries(repo_root: Path | str = ".") -> list[SubmoduleEntry]:
    root = Path(repo_root)
    gitmodules_path = root / ".gitmodules"
    if not gitmodules_path.exists():
        return []
    return parse_gitmodules_entries(gitmodules_path.read_text(encoding="utf-8"))


def managed_repo_slugs(paths: list[str]) -> list[str]:
    return sorted({repo_display_name(path) for path in paths})


def managed_repo_owners(paths: list[str]) -> list[str]:
    return sorted({repo_owner(path) for path in paths})


def find_submodules_with_marker(
    marker_file: str, repo_root: Path | str = "."
) -> list[str]:
    if not marker_file:
        raise ValueError("marker file is required")

    root = Path(repo_root)
    return SubmoduleFilter(marker_files=(marker_file,)).apply(
        read_gitmodules_paths(root), root
    )
