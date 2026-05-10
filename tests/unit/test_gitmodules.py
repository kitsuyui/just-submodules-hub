from pathlib import Path

from just_submodules_hub.gitmodules import (
    find_submodules_with_marker,
    managed_repo_owners,
    managed_repo_slugs,
    parse_gitmodules_entries,
    parse_gitmodules_paths,
)


def test_parse_gitmodules_paths() -> None:
    text = """
[submodule "repo/github.com/kitsuyui/ts-playground"]
    path = repo/github.com/kitsuyui/ts-playground
    url = https://github.com/kitsuyui/ts-playground
[submodule "repo/github.com/kitsuyui/react-playground"]
    path = repo/github.com/kitsuyui/react-playground
    url = https://github.com/kitsuyui/react-playground
"""
    paths = parse_gitmodules_paths(text)
    assert paths == [
        "repo/github.com/kitsuyui/ts-playground",
        "repo/github.com/kitsuyui/react-playground",
    ]
    assert managed_repo_slugs(paths) == [
        "kitsuyui/react-playground",
        "kitsuyui/ts-playground",
    ]
    assert managed_repo_owners(paths) == ["kitsuyui"]


def test_find_submodules_with_marker(tmp_path: Path) -> None:
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "repo/github.com/example-owner/one"]
    path = repo/github.com/example-owner/one
[submodule "repo/github.com/example-owner/two"]
    path = repo/github.com/example-owner/two
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "repo/github.com/example-owner/one").mkdir(parents=True)
    (tmp_path / "repo/github.com/example-owner/two").mkdir(parents=True)
    (tmp_path / "repo/github.com/example-owner/one/pyproject.toml").write_text(
        "[project]\nname='one'\n",
        encoding="utf-8",
    )

    assert find_submodules_with_marker("pyproject.toml", repo_root=tmp_path) == [
        "repo/github.com/example-owner/one",
    ]


def test_parse_gitmodules_paths_returns_empty_for_blank_text() -> None:
    assert parse_gitmodules_paths("") == []


def test_parse_gitmodules_entries_preserves_section_name_and_url() -> None:
    text = """
[submodule "custom.name"]
    path = repo/github.com/example-owner/example-repo
    url = git@github.com:example-owner/example-repo.git
""".strip()

    entries = parse_gitmodules_entries(text)

    assert len(entries) == 1
    assert entries[0].name == "custom.name"
    assert entries[0].path == "repo/github.com/example-owner/example-repo"
    assert entries[0].url == "git@github.com:example-owner/example-repo.git"
