from pathlib import Path

from just_submodules_hub.gitmodules import (
    find_submodules_with_marker,
    managed_repo_owners,
    managed_repo_slugs,
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
    assert managed_repo_slugs(paths) == ["kitsuyui/react-playground", "kitsuyui/ts-playground"]
    assert managed_repo_owners(paths) == ["kitsuyui"]


def test_find_submodules_with_marker(tmp_path: Path) -> None:
    (tmp_path / ".gitmodules").write_text(
        """
[submodule "repo/github.com/acme/one"]
    path = repo/github.com/acme/one
[submodule "repo/github.com/acme/two"]
    path = repo/github.com/acme/two
""".strip(),
        encoding="utf-8",
    )
    (tmp_path / "repo/github.com/acme/one").mkdir(parents=True)
    (tmp_path / "repo/github.com/acme/two").mkdir(parents=True)
    (tmp_path / "repo/github.com/acme/one/pyproject.toml").write_text("[project]\nname='one'\n", encoding="utf-8")

    assert find_submodules_with_marker("pyproject.toml", repo_root=tmp_path) == [
        "repo/github.com/acme/one"
    ]
