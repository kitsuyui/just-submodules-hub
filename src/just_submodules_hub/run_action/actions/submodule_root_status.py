"""Action handlers for submodule root-status visibility management."""

from __future__ import annotations

from just_submodules_hub.repo_paths import normalize_repo_input
from just_submodules_hub.run_action.actions import _helpers
from just_submodules_hub.run_action.registry import action


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


def _set_ignore_for_sections(repo_filter: str, value: str) -> int:
    """Set ``ignore = <value>`` for all submodules matching *repo_filter*.

    Iterates over matching submodule sections (all if *repo_filter* is empty)
    and calls :func:`_helpers.set_submodule_ignore_value` for each path.
    Returns 0 on success, non-zero on first failure.
    """
    for _section, path in _helpers._iter_submodule_sections(repo_filter):
        rc = _helpers.set_submodule_ignore_value(path, value)
        if rc != 0:
            return rc
    return 0


def _clear_ignore_for_sections(repo_filter: str) -> int:
    """Clear ``ignore`` for all submodules matching *repo_filter*.

    Iterates over matching submodule sections (all if *repo_filter* is empty)
    and calls :func:`_helpers.clear_submodule_ignore_value` for each path.
    Returns 0 on success, non-zero on first failure.
    """
    for _section, path in _helpers._iter_submodule_sections(repo_filter):
        rc = _helpers.clear_submodule_ignore_value(path)
        if rc != 0:
            return rc
    return 0


@action("submodule-root-status-hide")
def cmd_submodule_root_status_hide(args: list[str]) -> int:
    """Hide submodule root-status changes by setting ``ignore = all``.

    Optionally accepts a REPO argument to target a single submodule.
    """
    return _set_ignore_for_sections(_resolve_repo_filter(args), "all")


@action("submodule-root-status-show")
def cmd_submodule_root_status_show(args: list[str]) -> int:
    """Show submodule root-status changes by clearing the ``ignore`` setting.

    Optionally accepts a REPO argument to target a single submodule.
    """
    return _clear_ignore_for_sections(_resolve_repo_filter(args))


@action("submodule-root-status-visibility")
def cmd_submodule_root_status_visibility(args: list[str]) -> int:
    """Print hidden/visible status for each submodule (``ignore = all``).

    Optionally accepts a REPO argument to target a single submodule.
    """
    repo = _resolve_repo_filter(args)
    return _helpers.print_submodule_visibility_status("all", repo)
