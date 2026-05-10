from __future__ import annotations

from pathlib import Path

from just_submodules_hub.submodule_filters import SubmoduleFilter, filter_by_marker


def test_filter_by_marker_selects_matching_paths(tmp_path: Path) -> None:
    python_path = "repo/github.com/example/python-lib"
    js_path = "repo/github.com/example/js-lib"
    (tmp_path / python_path).mkdir(parents=True)
    (tmp_path / js_path).mkdir(parents=True)
    (tmp_path / python_path / "pyproject.toml").write_text(
        "[project]\n",
        encoding="utf-8",
    )
    (tmp_path / js_path / "package.json").write_text("{}\n", encoding="utf-8")

    assert filter_by_marker([python_path, js_path], "pyproject.toml", tmp_path) == [
        python_path,
    ]


def test_submodule_filter_applies_multiple_markers(tmp_path: Path) -> None:
    mixed_path = "repo/github.com/example/mixed"
    python_path = "repo/github.com/example/python-lib"
    (tmp_path / mixed_path).mkdir(parents=True)
    (tmp_path / python_path).mkdir(parents=True)
    (tmp_path / mixed_path / "pyproject.toml").write_text(
        "[project]\n",
        encoding="utf-8",
    )
    (tmp_path / mixed_path / "package.json").write_text("{}\n", encoding="utf-8")
    (tmp_path / python_path / "pyproject.toml").write_text(
        "[project]\n",
        encoding="utf-8",
    )

    selected = SubmoduleFilter(marker_files=("pyproject.toml", "package.json")).apply(
        [mixed_path, python_path],
        tmp_path,
    )

    assert selected == [mixed_path]
