"""Deprecated alias actions for submodule visibility management.

Each action here emits a deprecation warning and then delegates to the
current canonical implementation.  These exist for backward-compatibility
only; new callers should use the canonical action names.
"""

from __future__ import annotations

from just_submodules_hub.repo_paths import normalize_repo_input
from just_submodules_hub.run_action.actions import _helpers
from just_submodules_hub.run_action.registry import action, dispatch


def _resolve_repo_filter(args: list[str]) -> str:
    """Return a normalized submodule path filter from *args*, or empty for all.

    When a REPO argument is present, normalizes ``owner/name`` or full-path
    inputs to the canonical ``repo/github.com/owner/name`` form.
    An empty string means "apply to all submodules".
    """
    if not args:
        return ""
    raw = args[0]
    if not raw:
        return ""
    return normalize_repo_input(raw)


# ---------------------------------------------------------------------------
# Aliases for submodule-root-status-hide
# ---------------------------------------------------------------------------


@action("submodule-hide-root-status-changes")
def cmd_submodule_hide_root_status_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-hide`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-hide-root-status-changes",
        "submodule-root-status-hide",
    )
    return dispatch("submodule-root-status-hide", args)


@action("submodule-hide-worktree-changes")
def cmd_submodule_hide_worktree_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-hide`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-hide-worktree-changes",
        "submodule-root-status-hide",
    )
    return dispatch("submodule-root-status-hide", args)


@action("submodule-hide-all-changes")
def cmd_submodule_hide_all_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-hide`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-hide-all-changes",
        "submodule-root-status-hide",
    )
    return dispatch("submodule-root-status-hide", args)


@action("submodule-ignore-all-on")
def cmd_submodule_ignore_all_on(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-hide`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-all-on",
        "submodule-root-status-hide",
    )
    return dispatch("submodule-root-status-hide", args)


# ---------------------------------------------------------------------------
# Aliases for submodule-root-status-show
# ---------------------------------------------------------------------------


@action("submodule-show-root-status-changes")
def cmd_submodule_show_root_status_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-show`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-show-root-status-changes",
        "submodule-root-status-show",
    )
    return dispatch("submodule-root-status-show", args)


@action("submodule-show-worktree-changes")
def cmd_submodule_show_worktree_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-show`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-show-worktree-changes",
        "submodule-root-status-show",
    )
    return dispatch("submodule-root-status-show", args)


@action("submodule-show-all-changes")
def cmd_submodule_show_all_changes(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-show`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-show-all-changes",
        "submodule-root-status-show",
    )
    return dispatch("submodule-root-status-show", args)


@action("submodule-ignore-all-off")
def cmd_submodule_ignore_all_off(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-show`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-all-off",
        "submodule-root-status-show",
    )
    return dispatch("submodule-root-status-show", args)


# ---------------------------------------------------------------------------
# Aliases for submodule-root-status-visibility
# ---------------------------------------------------------------------------


@action("submodule-root-status-changes-visibility")
def cmd_submodule_root_status_changes_visibility(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-visibility`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-root-status-changes-visibility",
        "submodule-root-status-visibility",
    )
    return dispatch("submodule-root-status-visibility", args)


@action("submodule-worktree-changes-visibility")
def cmd_submodule_worktree_changes_visibility(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-visibility`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-worktree-changes-visibility",
        "submodule-root-status-visibility",
    )
    return dispatch("submodule-root-status-visibility", args)


@action("submodule-all-changes-visibility")
def cmd_submodule_all_changes_visibility(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-visibility`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-all-changes-visibility",
        "submodule-root-status-visibility",
    )
    return dispatch("submodule-root-status-visibility", args)


# ---------------------------------------------------------------------------
# Dirty-specific deprecated actions (not mere aliases; different ignore value)
# ---------------------------------------------------------------------------


@action("submodule-ignore-dirty-on")
def cmd_submodule_ignore_dirty_on(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-hide`` instead.

    This variant sets ``ignore = dirty`` rather than ``ignore = all``.
    """
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-dirty-on",
        "submodule-root-status-hide",
    )
    repo_filter = _resolve_repo_filter(args)
    for _section, path in _helpers._iter_submodule_sections(repo_filter):
        rc = _helpers.set_submodule_ignore_value(path, "dirty")
        if rc != 0:
            return rc
    return 0


@action("submodule-ignore-dirty-off")
def cmd_submodule_ignore_dirty_off(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-show`` instead."""
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-dirty-off",
        "submodule-root-status-show",
    )
    repo_filter = _resolve_repo_filter(args)
    for _section, path in _helpers._iter_submodule_sections(repo_filter):
        rc = _helpers.clear_submodule_ignore_value(path)
        if rc != 0:
            return rc
    return 0


@action("submodule-ignore-dirty-status")
def cmd_submodule_ignore_dirty_status(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-visibility`` instead.

    Prints raw ignore status for the ``dirty`` value.
    """
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-dirty-status",
        "submodule-root-status-visibility",
    )
    repo = _resolve_repo_filter(args)
    return _helpers.print_submodule_ignore_raw_status("dirty", repo)


@action("submodule-ignore-all-status")
def cmd_submodule_ignore_all_status(args: list[str]) -> int:
    """Deprecated: use ``submodule-root-status-visibility`` instead.

    Prints raw ignore status for the ``all`` value.
    """
    _helpers.warn_deprecated_submodule_action(
        "submodule-ignore-all-status",
        "submodule-root-status-visibility",
    )
    repo = _resolve_repo_filter(args)
    return _helpers.print_submodule_ignore_raw_status("all", repo)
