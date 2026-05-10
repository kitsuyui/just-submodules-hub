#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from typing import Any

from tqdm import tqdm

from just_submodules_hub.default_branch import resolve_default_branch as default_branch
from just_submodules_hub.default_heads import (
    fetch_default_heads_for_paths,
    matching_default_head,
    owner_prefilter_total,
)
from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.repo_paths import resolve_repo_input
from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    progress_bar,
    run_parallel,
    tick,
)

FIELDS = ("repo", "status", "action", "branch", "pr", "dirty", "message")


@dataclass(frozen=True)
class Result:
    repo: str
    status: str
    action: str
    branch: str
    pr: str
    dirty: str
    message: str


def run_git(
    repo: Path,
    args: list[str],
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=True,
        check=check,
    )


def summarize(proc: subprocess.CompletedProcess[str]) -> str:
    text = (proc.stderr or proc.stdout).strip()
    return " ".join(text.split()) or f"exit {proc.returncode}"


def current_branch(repo: Path) -> str:
    proc = run_git(repo, ["branch", "--show-current"])
    return proc.stdout.strip()


def current_head(repo: Path) -> str:
    proc = run_git(repo, ["rev-parse", "HEAD"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def dirty_state(repo: Path) -> str:
    proc = run_git(repo, ["status", "--porcelain"])
    if proc.returncode != 0:
        return "unknown"
    return "dirty" if proc.stdout.strip() else "clean"


def pull_ff_only(
    repo: Path,
    action: str,
    repo_label: str,
    branch: str,
    pr: str,
    dirty: str,
) -> Result:
    before = current_head(repo)
    proc = run_git(repo, ["pull", "--ff-only"])
    after = current_head(repo)
    if proc.returncode != 0:
        return Result(repo_label, "failed", action, branch, pr, dirty, summarize(proc))
    if before and after and before != after:
        return Result(
            repo_label,
            "updated",
            action,
            branch,
            pr,
            dirty,
            "fast-forwarded",
        )
    return Result(repo_label, "noop", action, branch, pr, dirty, "already up to date")


def gh_pr_view(repo: Path) -> tuple[str, str, str]:
    if shutil.which("gh") is None:
        return "", "", "gh not found"
    proc = subprocess.run(
        ["gh", "pr", "view", "--json", "number,state,mergedAt"],
        cwd=str(repo),
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return "", "", summarize(proc)
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return "", "", "gh returned invalid JSON"
    number = str(data.get("number") or "")
    state = str(data.get("state") or "").upper()
    merged_at = str(data.get("mergedAt") or "")
    if state == "MERGED" or (state == "CLOSED" and merged_at):
        return number, "merged", ""
    if state == "OPEN":
        return number, "open", ""
    if state == "CLOSED":
        return number, "closed", ""
    return number, state.lower() or "unknown", ""


def switch_default_and_pull(
    repo: Path,
    repo_label: str,
    branch: str,
    pr: str,
    dirty: str,
    default: str,
) -> Result:
    fetch_proc = run_git(repo, ["fetch", "origin", default])
    if fetch_proc.returncode != 0:
        return Result(
            repo_label,
            "failed",
            "fetch-default",
            branch,
            pr,
            dirty,
            summarize(fetch_proc),
        )
    switch_proc = run_git(repo, ["switch", default])
    if switch_proc.returncode != 0:
        return Result(
            repo_label,
            "failed",
            "switch-default",
            branch,
            pr,
            dirty,
            summarize(switch_proc),
        )
    pulled = pull_ff_only(repo, "switch-default", repo_label, default, pr, dirty)
    if pulled.status == "failed":
        return pulled
    return Result(
        repo_label,
        "settled",
        "switch-default",
        default,
        pr,
        dirty,
        "pr merged; switched to default branch",
    )


def detached_result(repo: Path, repo_label: str, dirty: str, default: str) -> Result:
    head = current_head(repo)
    if not head:
        return Result(
            repo_label,
            "failed",
            "detached",
            "",
            "",
            dirty,
            "cannot resolve HEAD",
        )
    fetch_proc = run_git(repo, ["fetch", "origin", default])
    if fetch_proc.returncode != 0:
        return Result(
            repo_label,
            "failed",
            "fetch-default",
            "",
            "",
            dirty,
            summarize(fetch_proc),
        )
    merge_base = run_git(
        repo,
        ["merge-base", "--is-ancestor", head, f"origin/{default}"],
    )
    if merge_base.returncode != 0:
        return Result(
            repo_label,
            "skipped",
            "detached-unknown",
            "",
            "",
            dirty,
            "detached HEAD is not on default branch",
        )
    switch_proc = run_git(repo, ["switch", default])
    if switch_proc.returncode != 0:
        return Result(
            repo_label,
            "failed",
            "detached-default",
            "",
            "",
            dirty,
            summarize(switch_proc),
        )
    pulled = pull_ff_only(repo, "detached-default", repo_label, default, "", dirty)
    if pulled.status == "failed":
        return pulled
    return Result(
        repo_label,
        "settled",
        "detached-default",
        default,
        "",
        dirty,
        "detached HEAD settled to default branch",
    )


def reconcile_one(root: Path, repo_path: str) -> Result:
    repo = root / repo_path
    if not repo.exists():
        return Result(
            repo_path,
            "failed",
            "inspect",
            "",
            "",
            "unknown",
            "submodule worktree does not exist",
        )
    if not (repo / ".git").exists():
        git_dir = run_git(repo, ["rev-parse", "--git-dir"])
        if git_dir.returncode != 0:
            return Result(
                repo_path,
                "failed",
                "inspect",
                "",
                "",
                "unknown",
                "not a git repository",
            )

    dirty = dirty_state(repo)
    branch = current_branch(repo)
    default = default_branch(repo)
    if not branch:
        return detached_result(repo, repo_path, dirty, default)
    if branch == default:
        return pull_ff_only(repo, "pull-default", repo_path, branch, "", dirty)

    pr, pr_state, pr_error = gh_pr_view(repo)
    if pr_state == "merged":
        return switch_default_and_pull(repo, repo_path, branch, pr, dirty, default)
    if pr_state == "open":
        return pull_ff_only(repo, "pull-topic", repo_path, branch, pr, dirty)
    if pr_state == "closed":
        return Result(
            repo_path,
            "skipped",
            "pr-closed",
            branch,
            pr,
            dirty,
            "pr closed without merge",
        )
    message = pr_error or "no pull request metadata"
    pulled = pull_ff_only(repo, "pull-topic", repo_path, branch, pr, dirty)
    if pulled.status == "failed":
        return Result(repo_path, "skipped", "pr-unknown", branch, pr, dirty, message)
    return Result(repo_path, pulled.status, "pull-topic", branch, pr, dirty, message)


def prefiltered_default_result(root: Path, repo_path: str, default: str) -> Result:
    repo = root / repo_path
    return Result(
        repo_path,
        "noop",
        "prefilter-default",
        default,
        "",
        dirty_state(repo),
        "already up to date",
    )


def build_reconcile_targets(
    root: Path,
    paths: list[str],
    *,
    prefilter: bool,
    bar: tqdm[Any] | None,
) -> tuple[list[str], list[Result]]:
    if not prefilter:
        return paths, []

    submodule_paths = [path for path in paths if path != "."]
    heads = fetch_default_heads_for_paths(submodule_paths, bar)
    targets: list[str] = []
    skipped: list[Result] = []

    for repo_path in paths:
        if repo_path == ".":
            targets.append(repo_path)
            continue
        default = matching_default_head(repo_path, heads)
        if default is None:
            targets.append(repo_path)
            continue
        skipped.append(prefiltered_default_result(root, repo_path, default.branch))
        tick(bar)

    return targets, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reconcile managed submodule worktrees.",
    )
    parser.add_argument("mode", choices=("one", "all", "root-and-all"))
    parser.add_argument("repo", nargs="?")
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=4,
        help="parallel workers for all mode (default: 4)",
    )
    parser.add_argument(
        "--prefilter",
        dest="prefilter",
        action="store_true",
        default=True,
        help=(
            "skip default-branch submodules that already match the remote default HEAD"
            " (default)"
        ),
    )
    parser.add_argument(
        "--no-prefilter",
        dest="prefilter",
        action="store_false",
        help="disable GraphQL prefilter",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = Path.cwd()
    if args.mode == "one":
        if not args.repo:
            print("repo is required for one mode", file=sys.stderr)
            return 2
        try:
            paths = [resolve_repo_input(args.repo, root)]
        except (ValueError, FileNotFoundError) as exc:
            print(str(exc), file=sys.stderr)
            return 2
    elif args.mode == "all":
        paths = read_gitmodules_paths(root)
    else:
        paths = [".", *read_gitmodules_paths(root)]

    if args.mode in ("all", "root-and-all"):
        prefilter_paths = [path for path in paths if path != "."]
        with progress_bar(
            total=len(paths) + owner_prefilter_total(prefilter_paths, args.prefilter),
            desc="reconcile",
            unit="repo",
        ) as bar:
            targets, results = build_reconcile_targets(
                root,
                paths,
                prefilter=args.prefilter,
                bar=bar,
            )
            target_results, failures = run_parallel(
                targets,
                lambda path: reconcile_one(root, path),
                jobs=args.jobs,
                on_done=lambda: tick(bar),
            )
            results.extend(target_results)
            results.extend(
                Result(
                    failure.item,
                    "failed",
                    "batch",
                    "",
                    "",
                    "unknown",
                    failure.message,
                )
                for failure in failures
            )
        results.sort(key=lambda result: result.repo)
    else:
        results = [reconcile_one(root, path) for path in paths]

    print_records(results, FIELDS, args.format)

    return 1 if any(result.status == "failed" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main())
