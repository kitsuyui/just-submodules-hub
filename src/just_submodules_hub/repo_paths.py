from __future__ import annotations

from configparser import ConfigParser
from pathlib import Path


REPO_PREFIX = "repo/github.com/"


def _strip_repo_transport(value: str) -> str:
    if not value:
        raise ValueError("repository input is required")

    normalized = value
    for prefix in ("git@github.com:", "https://github.com/"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


def normalize_repo_input(value: str) -> str:
    normalized = _strip_repo_transport(value)
    if normalized.startswith(REPO_PREFIX):
        return normalized
    if "/" not in normalized:
        raise ValueError(f"repository input must include owner and repo: {value}")
    return f"{REPO_PREFIX}{normalized}"


def _parse_gitmodules_paths(text: str) -> list[str]:
    if not text.strip():
        return []
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


def managed_repo_paths(hub_root: Path) -> list[str]:
    root = Path(hub_root)
    paths: set[str] = set()

    gitmodules_path = root / ".gitmodules"
    if gitmodules_path.exists():
        paths.update(_parse_gitmodules_paths(gitmodules_path.read_text(encoding="utf-8")))

    repos_root = root / REPO_PREFIX
    if repos_root.exists():
        for owner_dir in repos_root.iterdir():
            if not owner_dir.is_dir():
                continue
            for repo_dir in owner_dir.iterdir():
                if repo_dir.is_dir():
                    paths.add(str(repo_dir.relative_to(root)))

    return sorted(paths)


def resolve_repo_input(value: str, hub_root: Path) -> str:
    normalized = _strip_repo_transport(value)
    if normalized.startswith(REPO_PREFIX) or "/" in normalized:
        return normalize_repo_input(normalized)

    matches = [path for path in managed_repo_paths(hub_root) if Path(path).name == normalized]
    if not matches:
        raise FileNotFoundError(f"repository short name not found: {value}")
    if len(matches) > 1:
        names = ", ".join(repo_display_name(path) for path in matches)
        raise ValueError(f"repository short name is ambiguous: {value} -> {names}")
    return matches[0]


def repo_display_name(repo_path: str) -> str:
    if repo_path.startswith(REPO_PREFIX):
        return repo_path[len(REPO_PREFIX) :]
    return repo_path


def repo_owner(repo_path: str) -> str:
    return repo_display_name(repo_path).split("/", 1)[0]


def repo_abspath(value: str, hub_root: Path) -> Path:
    repo_path = hub_root / resolve_repo_input(value, hub_root)
    if not repo_path.exists():
        raise FileNotFoundError(f"repository path not found: {repo_path}")
    return repo_path.resolve()
