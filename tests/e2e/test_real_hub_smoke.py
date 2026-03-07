from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests.integration.helpers import add_submodule, init_hub


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = PROJECT_ROOT / "scripts/submodules/list-by-file.sh"


@pytest.mark.real_e2e
def test_real_public_repositories_are_detected_as_js_projects(tmp_path: Path) -> None:
    if os.environ.get("RUN_REAL_E2E") != "1":
        pytest.skip("real E2E is disabled")

    hub = tmp_path / "hub"
    init_hub(hub)
    add_submodule(hub, "https://github.com/kitsuyui/ts-playground.git", "repo/github.com/kitsuyui/ts-playground")
    add_submodule(
        hub,
        "https://github.com/kitsuyui/react-playground.git",
        "repo/github.com/kitsuyui/react-playground",
    )

    proc = subprocess.run(
        [str(SCRIPT), "package.json"],
        cwd=str(hub),
        text=True,
        capture_output=True,
        check=False,
    )

    assert proc.returncode == 0, proc.stderr
    lines = set(proc.stdout.splitlines())
    assert "repo/github.com/kitsuyui/ts-playground" in lines
    assert "repo/github.com/kitsuyui/react-playground" in lines
