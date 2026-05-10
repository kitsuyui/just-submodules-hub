"""Filtering helpers that select submodule paths by marker file presence."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class SubmoduleFilter:
    """Filter configuration that selects submodule paths by required marker files."""

    marker_files: tuple[str, ...] = field(default_factory=tuple)

    def apply(self, paths: Iterable[str], repo_root: Path | str = ".") -> list[str]:
        """Return paths that pass all marker-file filters."""
        root = Path(repo_root)
        selected = list(paths)
        for marker_file in self.marker_files:
            selected = filter_by_marker(selected, marker_file, root)
        return selected


def filter_by_marker(
    paths: Iterable[str],
    marker_file: str,
    repo_root: Path | str = ".",
) -> list[str]:
    """Return paths from *paths* that contain *marker_file* somewhere within them."""
    if not marker_file:
        raise ValueError("marker file is required")

    root = Path(repo_root)
    return [path for path in paths if any((root / path).rglob(marker_file))]
