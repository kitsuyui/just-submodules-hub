#!/usr/bin/env python3
"""Thin shim: delegates to just_submodules_hub.linked_worktree_inventory."""

from just_submodules_hub.linked_worktree_inventory import main

if __name__ == "__main__":
    raise SystemExit(main())
