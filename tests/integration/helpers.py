from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Mapping


def run(cmd: list[str], cwd: Path, env: Mapping[str, str] | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        env={**os.environ, **dict(env or {})},
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise AssertionError(f"command failed: {' '.join(cmd)}\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}")
    return proc.stdout.strip()


def init_repo(path: Path, branch: str = "main") -> None:
    path.mkdir(parents=True, exist_ok=True)
    run(["git", "init", "-b", branch], cwd=path)
    run(["git", "config", "user.name", "Test User"], cwd=path)
    run(["git", "config", "user.email", "test@example.com"], cwd=path)


def commit_file(repo: Path, relative_path: str, content: str, message: str) -> str:
    target = repo / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    run(["git", "add", relative_path], cwd=repo)
    run(["git", "commit", "-m", message], cwd=repo)
    return run(["git", "rev-parse", "HEAD"], cwd=repo)


def create_remote(tmp_path: Path, owner: str, name: str, files: Mapping[str, str], branch: str = "main") -> Path:
    seed = tmp_path / f"{name}-seed"
    remote = tmp_path / f"{name}.git"
    init_repo(seed, branch=branch)
    for relative_path, content in files.items():
        commit_file(seed, relative_path, content, f"Add {relative_path}")
    run(["git", "clone", "--bare", str(seed), str(remote)], cwd=tmp_path)
    return remote


def clone_remote(remote: Path, destination: Path) -> None:
    run(["git", "clone", str(remote), str(destination)], cwd=destination.parent)
    run(["git", "config", "user.name", "Test User"], cwd=destination)
    run(["git", "config", "user.email", "test@example.com"], cwd=destination)


def init_hub(path: Path) -> None:
    init_repo(path)
    run(["git", "config", "protocol.file.allow", "always"], cwd=path)


def add_submodule(hub: Path, remote: Path | str, submodule_path: str) -> None:
    run(["git", "-c", "protocol.file.allow=always", "submodule", "add", str(remote), submodule_path], cwd=hub)
    run(["git", "commit", "-m", f"Add {submodule_path}"], cwd=hub)


def advance_remote(remote: Path, relative_path: str, content: str, message: str, branch: str = "main") -> str:
    with tempfile.TemporaryDirectory() as tmpdir:
        checkout = Path(tmpdir) / "checkout"
        clone_remote(remote, checkout)
        run(["git", "switch", branch], cwd=checkout)
        head = commit_file(checkout, relative_path, content, message)
        run(["git", "push", "origin", branch], cwd=checkout)
        return head


def git_head(repo: Path) -> str:
    return run(["git", "rev-parse", "HEAD"], cwd=repo)


def write_executable(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    path.chmod(0o755)
