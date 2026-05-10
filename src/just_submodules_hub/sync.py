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
    repo_path: str
    default_branch: str
    switched: bool
    updated: bool
    skipped: bool = False
    skip_reason: str = ""


@dataclass
class ConfigSnapshot:
    cwd: Path
    key: str
    had_value: bool
    value: str = ""


@dataclass
class RemoteSnapshot:
    cwd: Path
    url: str


def positive_int(raw: str) -> int:
    return batch_positive_int(raw)


def parse_repo_paths(repo_root: Path | str = ".") -> list[str]:
    return read_gitmodules_paths(repo_root)


def should_sync_target(
    remote_head: tuple[str, str] | DefaultHead | None,
    local_branch: str,
    local_oid: str,
) -> bool:
    if remote_head is None:
        return True
    if isinstance(remote_head, DefaultHead):
        remote_branch, remote_oid = remote_head.branch, remote_head.oid
    else:
        remote_branch, remote_oid = remote_head
    return not (local_branch == remote_branch and local_oid == remote_oid)


def github_token_url(url: str, token: str) -> str | None:
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
    encoded = quote(secret, safe="")
    return [value for value in {secret, encoded} if value]


def redact_secrets(text: str, redactions: Iterable[str]) -> str:
    redacted = text
    for secret in redactions:
        if secret:
            redacted = redacted.replace(secret, "<redacted>")
    return redacted


def git_config_get(cwd: Path, key: str) -> tuple[bool, str]:
    try:
        return True, run(["git", "config", "--local", "--get", key], cwd=cwd)
    except RuntimeError:
        return False, ""


def git_config_set(cwd: Path, key: str, value: str) -> None:
    run(["git", "config", "--local", key, value], cwd=cwd)


def git_config_unset(cwd: Path, key: str) -> None:
    with suppress(RuntimeError):
        run(["git", "config", "--local", "--unset", key], cwd=cwd)


def restore_parent_config(snapshot: ConfigSnapshot) -> None:
    if snapshot.had_value:
        git_config_set(snapshot.cwd, snapshot.key, snapshot.value)
    else:
        git_config_unset(snapshot.cwd, snapshot.key)


def restore_remote(snapshot: RemoteSnapshot) -> None:
    run(["git", "remote", "set-url", "origin", snapshot.url], cwd=snapshot.cwd)


def apply_token_url_overrides(
    entries: list[SubmoduleEntry],
    token: str,
    repo_root: Path,
    parent_snapshots: list[ConfigSnapshot],
    remote_snapshots: list[RemoteSnapshot],
) -> None:
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
    if token_env is None:
        yield []
        return

    token = os.environ.get(token_env)
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
        if restore_errors and sys.exc_info()[0] is None:
            raise RuntimeError(
                "Failed to restore tokenized submodule URLs: "
                + "; ".join(restore_errors),
            )


def build_sync_targets(
    paths: Iterable[str],
    prefilter: bool,
    bar: tqdm[Any] | None,
) -> list[str]:
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
    cwd = Path(repo_path)
    if not (cwd / ".git").exists():
        raise RuntimeError(f"Repository path not found: {repo_path}")

    current_branch = "DETACHED"
    with suppress(Exception):
        current_branch = run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=cwd,
        )

    status_porcelain = run(["git", "status", "--porcelain"], cwd=cwd)
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
    name = repo_display_name(result.repo_path)
    rendered = render_sync_result(name, result, verbose)
    if rendered is None:
        return False
    print(rendered)
    return not result.skipped


def render_sync_result(name: str, result: SyncResult, verbose: bool) -> str | None:
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
    for failure in failures:
        message = redact_secrets(failure.message, redactions)
        print(f"{repo_display_name(failure.item)}: {message}", file=sys.stderr)


def run_final_submodule_update() -> None:
    print(
        "Running final submodule update (--remote --rebase --recursive --recommend-shallow)...",
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
    parser = argparse.ArgumentParser(description="Sync submodules to default branches")
    subparsers = parser.add_subparsers(dest="action", required=True)

    one = subparsers.add_parser("one", help="sync one repository")
    one.add_argument(
        "repo_path",
        help="repository name or path (e.g. example, owner/repo, or repo/github.com/owner/repo)",
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
        help="temporarily authenticate GitHub submodule URLs with the token stored in ENV",
    )
    all_cmd.add_argument(
        "--final-submodule-update",
        action="store_true",
        help="run git submodule update --remote after successful sync",
    )
    return parser


def handle_one_action(args: argparse.Namespace) -> int:
    result = sync_one(resolve_repo_input(args.repo_path, Path.cwd()))
    print_result(result, args.verbose)
    if result.skipped:
        return 1
    return 0


def handle_all_action(args: argparse.Namespace) -> int:
    with temporary_github_submodule_credentials(
        getattr(args, "token_env", None),
    ) as redactions:
        paths = parse_repo_paths()
        if not paths:
            print("No submodule paths found in .gitmodules")
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
                print("All submodules are up to date.")
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
            print("All submodules are up to date.")
        return code


def main() -> int:
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
