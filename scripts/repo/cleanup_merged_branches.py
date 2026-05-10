#!/usr/bin/env python3
"""Thin shim: delegates to just_submodules_hub.branch_cleanup."""

from just_submodules_hub.branch_cleanup import main

if __name__ == "__main__":
    raise SystemExit(main())
