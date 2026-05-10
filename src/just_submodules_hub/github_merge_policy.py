"""Constants and helpers for GitHub repository merge policy (squash/merge/rebase)."""

from __future__ import annotations

MERGE_POLICY_FIELDS = (
    "nameWithOwner,visibility,mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed"
)
MERGE_METHODS = ("merge-commit", "squash", "rebase")

FIELD_BY_METHOD = {
    "merge-commit": "mergeCommitAllowed",
    "squash": "squashMergeAllowed",
    "rebase": "rebaseMergeAllowed",
}

PATCH_FIELD_BY_METHOD = {
    "merge-commit": "allow_merge_commit",
    "squash": "allow_squash_merge",
    "rebase": "allow_rebase_merge",
}


def merge_method_allowed(payload: dict, method: str) -> bool:
    """Return True when *method* is enabled in the repository API *payload*."""
    return bool(payload.get(FIELD_BY_METHOD[method]))


def merge_method_patch_payload(method: str, enabled: bool) -> dict[str, bool]:
    """Build a PATCH request body that sets *method* to *enabled*."""
    return {PATCH_FIELD_BY_METHOD[method]: enabled}


def summarize_merge_method(
    repo: str,
    visibility: str,
    method: str,
    payload: dict,
) -> dict:
    """Return a summary dict describing the allowed status of *method* for *repo*."""
    return {
        "repo": repo,
        "visibility": visibility.lower(),
        "method": method,
        "allowed": merge_method_allowed(payload, method),
    }
