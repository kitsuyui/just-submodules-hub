from __future__ import annotations

import subprocess
from pathlib import Path

from .helpers import add_submodule, create_remote


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/submodules/list-by-file.sh"


def test_list_by_file_script_lists_matching_submodules(tmp_path: Path, hub_repo: Path) -> None:
    python_remote = create_remote(
        tmp_path,
        "acme",
        "python-lib",
        {"pyproject.toml": "[project]\nname='python-lib'\n"},
    )
    js_remote = create_remote(
        tmp_path,
        "acme",
        "js-lib",
        {"package.json": '{"name":"js-lib"}\n'},
    )
    add_submodule(hub_repo, python_remote, "repo/github.com/acme/python-lib")
    add_submodule(hub_repo, js_remote, "repo/github.com/acme/js-lib")

    proc = subprocess.run(
        [str(SCRIPT), "pyproject.toml"],
        cwd=str(hub_repo),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == ["repo/github.com/acme/python-lib"]
