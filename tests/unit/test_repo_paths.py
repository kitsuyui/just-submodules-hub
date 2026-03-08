from pathlib import Path

import pytest

from just_submodules_hub.repo_paths import (
    managed_repo_paths,
    normalize_repo_input,
    repo_abspath,
    repo_display_name,
    repo_owner,
    resolve_repo_input,
)


def test_normalize_repo_input_accepts_slug() -> None:
    assert normalize_repo_input("kitsuyui/example") == "repo/github.com/kitsuyui/example"


def test_normalize_repo_input_accepts_https_url() -> None:
    assert normalize_repo_input("https://github.com/kitsuyui/example.git") == "repo/github.com/kitsuyui/example"


def test_normalize_repo_input_accepts_ssh_url() -> None:
    assert normalize_repo_input("git@github.com:kitsuyui/example.git") == "repo/github.com/kitsuyui/example"


def test_repo_helpers_strip_prefix() -> None:
    repo_path = "repo/github.com/kitsuyui/example"
    assert repo_display_name(repo_path) == "kitsuyui/example"
    assert repo_owner(repo_path) == "kitsuyui"


def test_normalize_repo_input_rejects_missing_repo_name() -> None:
    try:
        normalize_repo_input("kitsuyui")
    except ValueError as exc:
        assert "owner and repo" in str(exc)
    else:
        raise AssertionError("normalize_repo_input should reject invalid input")


def test_repo_helpers_accept_plain_slug() -> None:
    assert repo_display_name("kitsuyui/example") == "kitsuyui/example"
    assert repo_owner("kitsuyui/example") == "kitsuyui"


def test_managed_repo_paths_reads_gitmodules(tmp_path: Path) -> None:
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "repo/github.com/kitsuyui/example"]
    path = repo/github.com/kitsuyui/example
[submodule "repo/github.com/acme/demo"]
    path = repo/github.com/acme/demo
""".strip()
        + "\n",
        encoding="utf-8",
    )

    assert managed_repo_paths(tmp_path) == [
        "repo/github.com/acme/demo",
        "repo/github.com/kitsuyui/example",
    ]


def test_resolve_repo_input_accepts_short_name_when_unique(tmp_path: Path) -> None:
    repo = tmp_path / "repo/github.com/kitsuyui/example"
    repo.mkdir(parents=True)

    assert resolve_repo_input("example", tmp_path) == "repo/github.com/kitsuyui/example"


def test_resolve_repo_input_rejects_ambiguous_short_name(tmp_path: Path) -> None:
    (tmp_path / "repo/github.com/kitsuyui/example").mkdir(parents=True)
    (tmp_path / "repo/github.com/acme/example").mkdir(parents=True)

    with pytest.raises(ValueError, match="ambiguous"):
        resolve_repo_input("example", tmp_path)


def test_resolve_repo_input_rejects_missing_short_name(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="short name not found"):
        resolve_repo_input("example", tmp_path)


def test_repo_abspath_resolves_existing_repository(tmp_path: Path) -> None:
    repo = tmp_path / "repo/github.com/kitsuyui/example"
    repo.mkdir(parents=True)

    assert repo_abspath("kitsuyui/example", tmp_path) == repo.resolve()


def test_repo_abspath_resolves_existing_repository_from_short_name(tmp_path: Path) -> None:
    repo = tmp_path / "repo/github.com/kitsuyui/example"
    repo.mkdir(parents=True)

    assert repo_abspath("example", tmp_path) == repo.resolve()


def test_repo_abspath_rejects_missing_repository(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="repository path not found"):
        repo_abspath("kitsuyui/example", tmp_path)
