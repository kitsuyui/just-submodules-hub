from __future__ import annotations

from pathlib import Path

import pytest

from .helpers import init_hub


@pytest.fixture
def hub_repo(tmp_path: Path) -> Path:
    hub = tmp_path / "hub"
    init_hub(hub)
    return hub
