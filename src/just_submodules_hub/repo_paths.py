from __future__ import annotations


REPO_PREFIX = "repo/github.com/"


def normalize_repo_input(value: str) -> str:
    if not value:
        raise ValueError("repository input is required")
    if value.startswith(REPO_PREFIX):
        return value

    normalized = value
    for prefix in ("git@github.com:", "https://github.com/"):
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    if "/" not in normalized:
        raise ValueError(f"repository input must include owner and repo: {value}")
    return f"{REPO_PREFIX}{normalized}"


def repo_display_name(repo_path: str) -> str:
    if repo_path.startswith(REPO_PREFIX):
        return repo_path[len(REPO_PREFIX) :]
    return repo_path


def repo_owner(repo_path: str) -> str:
    return repo_display_name(repo_path).split("/", 1)[0]
