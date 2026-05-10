"""Entry point for ``python -m just_submodules_hub.run_action``."""

from __future__ import annotations

import sys

from just_submodules_hub.run_action.cli import main

raise SystemExit(main(sys.argv[1:]))
