"""CLI and library for syncing submodule repositories to their default branches."""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from tqdm import tqdm

from .default_branch import (
    parse_head_branch_line,  # noqa: F401
    resolve_default_branch,
)
from .default_heads import (
    DefaultHead,
    fetch_owner_default_heads,
    local_head,
    owner_prefilter_total,
)
from .gitmodules import SubmoduleEntry, read_gitmodules_entries, read_gitmodules_paths
from .repo_paths import repo_display_name, repo_owner, resolve_repo_input
from .shell import run
from .submodule_batch import (
    BatchFailure,
    progress_bar,
    run_parallel,
    tick,
)
from .submodule_batch import (
    positive_int as batch_positive_int,
)


@dataclass
class SyncResult:
    """Outcome of syncing a single submodule repository."""

    repo_path: str
    default_branch: str
    switched: bool
    updated: bool
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ConfigSnapshot:
    """Saved git-config entry to restore after a temporary token override."""

    cwd: Path
    key: str
    had_value: bool
    value: str = ""


@dataclass
class RemoteSnapshot:
    """Saved remote URL to restore after a temporary token-authenticated URL override.

    Used to roll back URL changes when token auth is no longer needed.
    """

    cwd: Path
    url: str


def positive_int(raw: str) -> int:
    """Delegate to submodule_batch.positive_int for CLI argument validation."""
    return batch_positive_int(raw)


def parse_repo_paths(repo_root: Path | str = ".") -> list[str]:
    """Return submodule paths listed in *repo_root*/.gitmodules."""
    return read_gitmodules_paths(repo_root)


def should_sync_target(
    remote_head: tuple[str, str] | DefaultHead | None,
    local_branch: str,
    local_oid: str,
) -> bool:
    """Return True when the local repo differs from *remote_head* and needs syncing."""
    if remote_head is None:
        return True
    if isinstance(remote_head, DefaultHead):
        remote_branch, remote_oid = remote_head.branch, remote_head.oid
    else:
        remote_branch, remote_oid = remote_head
    return not (local_branch == remote_branch and local_oid == remote_oid)


def github_token_url(url: str, token: str) -> str | None:
    """Rewrite *url* to embed *token* as HTTPS basic-auth credentials.

    Returns None when *url* is empty or not a recognizable GitHub URL form.
    """
    if not url:
        return None

    path: str | None = None
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:")
    elif url.startswith("ssh://git@github.com/"):
        path = url.removeprefix("ssh://git@github.com/")
    else:
        parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname == "github.com":
            path = parsed.path.lstrip("/")

    if not path:
        return None

    credential = f"x-access-token:{quote(token, safe='')}"
    return f"https://{credential}@github.com/{path}"


def redaction_values(secret: str) -> list[str]:
    """Return the raw and URL-encoded forms of *secret* for use as redactions."""
    if not secret or not secret.strip():
        return []
    encoded = quote(secret, safe="")
    return [value for value in {secret, encoded} if value]


def redact_secrets(text: str, redactions: Iterable[str]) -> str:
    """Replace each non-empty string in *redactions* inside *text*.

    Each matching secret is replaced with the literal string ``<redacted>``.
    """
    redacted = text
    for secret in redactions:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def git_config_get(cwd: Path, key: str) -> tuple[bool, str]:
    """Return (found, value) from local git config for *key* in *cwd*."""
    try:
        return True, run(["git", "config", "--local", "--get", key], cwd=cwd)
    except RuntimeError:
        return False, ""


def git_config_set(cwd: Path, key: str, value: str) -> None:
    """Set local git config *key* to *value* in *cwd*."""
    run(["git", "config", "--local", key, value], cwd=cwd)


def git_config_unset(cwd: Path, key: str) -> None:
    """Unset local git config *key* in *cwd*, ignoring errors if the key is absent."""
    with suppress(RuntimeError):
        run(["git", "config", "--local", "--unset", key], cwd=cwd)


def restore_parent_config(snapshot: ConfigSnapshot) -> None:
    """Restore the git-config entry saved in *snapshot* to its previous state."""
    if snapshot.had_value:
        git_config_set(snapshot.cwd, snapshot.key, snapshot.value)
    else:
        git_config_unset(snapshot.cwd, snapshot.key)


def restore_remote(snapshot: RemoteSnapshot) -> None:
    """Restore the remote origin URL saved in *snapshot*."""
    run(["git", "remote", "set-url", "origin", snapshot.url], cwd=snapshot.cwd)


def apply_token_url_overrides(
    entries: list[SubmoduleEntry],
    token: str,
    repo_root: Path,
    parent_snapshots: list[ConfigSnapshot],
    remote_snapshots: list[RemoteSnapshot],
) -> None:
    """Temporarily embed *token* into git-config and remote URLs for each entry."""
    for entry in entries:
        key = f"submodule.{entry.name}.url"
        had_parent_url, parent_url = git_config_get(repo_root, key)
        source_parent_url = parent_url or entry.url
        token_parent_url = github_token_url(source_parent_url, token)
        if token_parent_url is not None and token_parent_url != parent_url:
            parent_snapshots.append(
                ConfigSnapshot(repo_root, key, had_parent_url, parent_url),
            )
            git_config_set(repo_root, key, token_parent_url)

        submodule_path = repo_root / entry.path
        if not (submodule_path / ".git").exists():
            continue
        try:
            origin_url = run(["git", "remote", "get-url", "origin"], cwd=submodule_path)
        except RuntimeError:
            continue
        token_origin_url = github_token_url(origin_url, token)
        if token_origin_url is not None and token_origin_url != origin_url:
            remote_snapshots.append(RemoteSnapshot(submodule_path, origin_url))
            run(
                ["git", "remote", "set-url", "origin", token_origin_url],
                cwd=submodule_path,
            )


@contextmanager
def temporary_github_submodule_credentials(
    token_env: str | None,
    repo_root: Path | str = ".",
) -> Iterator[list[str]]:
    """Context manager that temporarily injects a GitHub token into submodule URLs.

    Yields a list of redaction strings. On exit, all overrides are restored.
    Raises RuntimeError if the named environment variable is unset.
    """
    if token_env is None:
        yield []
        return

    raw_token = os.environ.get(token_env, "")
    token = raw_token.strip()
    if not token:
        raise RuntimeError(f"Environment variable {token_env} is not set")

    root = Path(repo_root)
    redactions = redaction_values(token)
    parent_snapshots: list[ConfigSnapshot] = []
    remote_snapshots: list[RemoteSnapshot] = []
    restore_errors: list[str] = []

    try:
        apply_token_url_overrides(
            read_gitmodules_entries(root),
            token,
            root,
            parent_snapshots,
            remote_snapshots,
        )
        yield redactions
    except RuntimeError as err:
        raise RuntimeError(redact_secrets(str(err), redactions)) from err
    finally:
        for remote_snapshot in reversed(remote_snapshots):
            try:
                restore_remote(remote_snapshot)
            except RuntimeError as err:
                restore_errors.append(redact_secrets(str(err), redactions))
        for parent_snapshot in reversed(parent_snapshots):
            try:
                restore_parent_config(parent_snapshot)
            except RuntimeError as err:
                restore_errors.append(redact_secrets(str(err), redactions))
        if restore_errors:
            message = "Failed to restore tokenized submodule URLs: " + "; ".join(
                restore_errors
            )
            in_flight = sys.exc_info()[1]
            if in_flight is None:
                raise RuntimeError(message)
            # The body is unwinding via another exception; attach the
            # restore failures so tokenized URLs lingering in .git/config
            # are not silently dropped from the caller's view.
            in_flight.add_note(message)
            print(f"warning: {message}", file=sys.stderr)


def build_sync_targets(
    paths: Iterable[str],
    prefilter: bool,
    bar: tqdm[Any] | None,
) -> list[str]:
    """Return the subset of *paths* that need syncing.

    When *prefilter* is True, queries remote default-branch OIDs and skips repos
    that are already up to date.
    """
    path_list = list(paths)
    if not prefilter:
        return path_list

    heads: dict[str, DefaultHead | tuple[str, str]] = {}

    for owner in sorted({repo_owner(path) for path in path_list}):
        heads.update(fetch_owner_default_heads(owner, bar))

    targets: list[str] = []

    for repo_path in path_list:
        slug = repo_display_name(repo_path)
        remote = heads.get(slug)
        local_branch, local_oid = local_head(repo_path)
        if not should_sync_target(remote, local_branch, local_oid):
            tick(bar)
            continue
        targets.append(repo_path)

    return targets


def sync_one(repo_path: str) -> SyncResult:
    """Fetch, switch, and pull a single submodule repository."""
    cwd = Path(repo_path)
    if not (cwd / ".git").exists():
        raise RuntimeError(f"Repository path not found: {repo_path}")

    current_branch = "DETACHED"
    with suppress(Exception):
        current_branch = run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=cwd,
        )

    status_porcelain = run(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=cwd,
    )
    if status_porcelain:
        return SyncResult(
            repo_path=repo_path,
            default_branch=current_branch,
            switched=False,
            updated=False,
            skipped=True,
            skip_reason="dirty working tree",
        )

    run(["git", "fetch", "origin", "--prune"], cwd=cwd)
    # `git fetch` does not update `refs/remotes/origin/HEAD`, so when the
    # upstream renames its default branch the local symbolic-ref keeps
    # pointing at the stale name. Refresh it best-effort so that
    # `resolve_default_branch` (which queries the symbolic-ref first)
    # picks up the rename.
    with suppress(Exception):
        run(["git", "remote", "set-head", "origin", "-a"], cwd=cwd)
    default_branch = resolve_default_branch(repo_path, fallback=None)

    switched = current_branch != default_branch
    run(["git", "switch", default_branch], cwd=cwd)

    before = run(["git", "rev-parse", "HEAD"], cwd=cwd)
    run(["git", "pull", "--ff-only", "origin", default_branch], cwd=cwd)
    after = run(["git", "rev-parse", "HEAD"], cwd=cwd)

    return SyncResult(
        repo_path=repo_path,
        default_branch=default_branch,
        switched=switched,
        updated=before != after,
    )


def print_result(result: SyncResult, verbose: bool) -> bool:
    """Print the sync outcome to stdout and return True when the repo changed."""
    name = repo_display_name(result.repo_path)
    rendered = render_sync_result(name, result, verbose)
    if rendered is None:
        return False
    print(rendered)
    return not result.skipped


def render_sync_result(name: str, result: SyncResult, verbose: bool) -> str | None:
    """Format a human-readable line for *result*, or None to suppress output."""
    if result.skipped:
        return f"{name}: skipped ({result.skip_reason})"

    if not result.switched and not result.updated:
        if verbose:
            return f"{name}: up-to-date"
        return None

    parts: list[str] = []
    if result.switched:
        parts.append(f"switched-to:{result.default_branch}")
    if result.updated:
        parts.append("updated-to:latest")
    return f"{name}: {' '.join(parts)}"


def sync_all(
    paths: list[str],
    jobs: int,
    verbose: bool,
    bar: tqdm[Any] | None,
    redactions: Iterable[str] = (),
) -> tuple[int, int]:
    """Sync all *paths* in parallel and return (exit_code, changed_count)."""
    results, failures = run_parallel(
        paths,
        sync_one,
        jobs=jobs,
        on_done=lambda: tick(bar),
    )

    changed_count = 0
    skipped_count = 0
    for result in sorted(results, key=lambda r: r.repo_path):
        if result.skipped:
            skipped_count += 1
        if print_result(result, verbose):
            changed_count += 1

    if failures:
        print_failures(failures, redactions)
        print("One or more repositories failed to sync", file=sys.stderr)
        return 1, changed_count
    if skipped_count:
        print("One or more repositories were skipped", file=sys.stderr)
        return 1, changed_count
    return 0, changed_count


def print_failures(
    failures: list[BatchFailure],
    redactions: Iterable[str] = (),
) -> None:
    """Print each BatchFailure to stderr with secrets redacted."""
    for failure in failures:
        message = redact_secrets(failure.message, redactions)
        print(f"{repo_display_name(failure.item)}: {message}", file=sys.stderr)


def run_final_submodule_update() -> None:
    """Run git submodule update --remote --rebase --recursive --recommend-shallow."""
    print(
        "Running final submodule update"
        " (--remote --rebase --recursive --recommend-shallow)...",
        file=sys.stderr,
    )
    run(
        [
            "git",
            "submodule",
            "update",
            "--remote",
            "--rebase",
            "--recursive",
            "--recommend-shallow",
            "--progress",
        ],
    )


def build_parser() -> argparse.ArgumentParser:
    """Build and return the argument parser for the sync CLI."""
    parser = argparse.ArgumentParser(description="Sync submodules to default branches")
    subparsers = parser.add_subparsers(dest="action", required=True)

    one = subparsers.add_parser("one", help="sync one repository")
    one.add_argument(
        "repo_path",
        help="repository name or path"
        " (e.g. example, owner/repo, or repo/github.com/owner/repo)",
    )
    one.add_argument(
        "--verbose",
        action="store_true",
        help="show up-to-date repositories",
    )

    all_cmd = subparsers.add_parser(
        "all",
        help="sync all repositories from .gitmodules",
    )
    all_cmd.add_argument(
        "--jobs",
        type=positive_int,
        default=4,
        help="parallel workers (default: 4)",
    )
    all_cmd.add_argument(
        "--verbose",
        action="store_true",
        help="show up-to-date repositories",
    )
    all_cmd.add_argument(
        "--prefilter",
        dest="prefilter",
        action="store_true",
        default=True,
        help="enable GraphQL prefilter (default)",
    )
    all_cmd.add_argument(
        "--no-prefilter",
        dest="prefilter",
        action="store_false",
        help="disable GraphQL prefilter",
    )
    all_cmd.add_argument(
        "--token-env",
        metavar="ENV",
        help="temporarily authenticate GitHub submodule URLs"
        " with the token stored in ENV",
    )
    all_cmd.add_argument(
        "--final-submodule-update",
        action="store_true",
        help="run git submodule update --remote after successful sync",
    )
    return parser


def handle_one_action(args: argparse.Namespace) -> int:
    """Handle the ``sync one`` sub-command."""
    result = sync_one(resolve_repo_input(args.repo_path, Path.cwd()))
    print_result(result, args.verbose)
    if result.skipped:
        return 1
    return 0


def handle_all_action(args: argparse.Namespace) -> int:
    """Handle the ``sync all`` sub-command."""
    with temporary_github_submodule_credentials(
        getattr(args, "token_env", None),
    ) as redactions:
        paths = parse_repo_paths()
        if not paths:
            print("No submodule paths found in .gitmodules", file=sys.stderr)
            if getattr(args, "final_submodule_update", False):
                run_final_submodule_update()
            return 0

        with progress_bar(
            total=len(paths) + owner_prefilter_total(paths, args.prefilter),
            desc="sync-all",
            unit="task",
        ) as bar:
            targets = build_sync_targets(paths, args.prefilter, bar)
            if not targets:
                print("All submodules are up to date.", file=sys.stderr)
                if getattr(args, "final_submodule_update", False):
                    run_final_submodule_update()
                return 0
            code, changed_count = sync_all(
                targets,
                args.jobs,
                args.verbose,
                bar,
                redactions,
            )

        if code == 0 and getattr(args, "final_submodule_update", False):
            run_final_submodule_update()
        if code == 0 and changed_count == 0 and not args.verbose:
            print("All submodules are up to date.", file=sys.stderr)
        return code


def main() -> int:
    """Entry point for the sync CLI; parse args and dispatch to the right handler."""
    parser = build_parser()
    args = parser.parse_args()
    action = args.action

    try:
        if action == "one":
            return handle_one_action(args)

        if action == "all":
            return handle_all_action(args)

        print(f"Unknown sync action: {action}", file=sys.stderr)
        return 2
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 1
