from __future__ import annotations

from pathlib import Path

from just_submodules_hub.repo_paths import repo_abspath
from just_submodules_hub.shell import run


def opener_command(tool: str, repo_path: Path) -> list[str]:
    normalized_tool = tool.lower()
    repo = str(repo_path)

    if normalized_tool == "codex":
        return ["open", "-a", "Codex", repo]
    if normalized_tool in {"code", "vscode", "vs-code"}:
        return ["code", repo]
    if normalized_tool in {"iterm", "iterm2"}:
        return ["open", "-a", "iTerm", repo]
    raise ValueError(f"unsupported tool: {tool}")


def open_repo_in_tool(tool: str, repo: str, hub_root: Path) -> None:
    repo_path = repo_abspath(repo, hub_root)
    run(opener_command(tool, repo_path), cwd=hub_root)
