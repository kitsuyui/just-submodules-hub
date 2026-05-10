#!/usr/bin/env python3
"""Thin shim: delegates to just_submodules_hub.submodule_worktree_reconcile."""

from just_submodules_hub.submodule_worktree_reconcile import main

if __name__ == "__main__":
    raise SystemExit(main())
