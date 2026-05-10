#!/usr/bin/env python3
"""Thin shim: delegates to just_submodules_hub.linked_worktree_safety."""

from just_submodules_hub.linked_worktree_safety import main

if __name__ == "__main__":
    raise SystemExit(main())
