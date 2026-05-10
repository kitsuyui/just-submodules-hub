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
from just_submodules_hub.default_branch import resolve_default_branch
from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    run_parallel_with_progress,
)

FIELDS = ("repo", "target", "branch", "status", "reason")


@dataclass(frozen=True)
class BranchResult:
    repo: str
    target: str
    branch: str
    status: str
    reason: str


@dataclass(frozen=True)
class BranchState:
    default_branch: str
    current_branch: str
    local_branches: tuple[str, ...]
    remote_branches: tuple[str, ...]
    merged_pr_heads: frozenset[str]
    owned_merged_pr_heads: frozenset[str]
    open_pr_heads: frozenset[str]


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )


def run_gh(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["gh", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )


def lines(proc: subprocess.CompletedProcess[str]) -> tuple[str, ...]:
    return tuple(line.strip() for line in proc.stdout.splitlines() if line.strip())


def current_branch(repo: Path) -> str:
    proc = run_git(repo, ["branch", "--show-current"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def local_branches(repo: Path) -> tuple[str, ...]:
    proc = run_git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to list local branches")
    return lines(proc)


def remote_branches(repo: Path, remote: str) -> tuple[str, ...]:
    proc = run_git(repo, ["ls-remote", "--heads", remote])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to list remote branches")
    values: list[str] = []
    for line in lines(proc):
        parts = line.split(None, 1)
        if len(parts) != 2:
            continue
        ref = parts[1]
        prefix = "refs/heads/"
        if ref.startswith(prefix):
            values.append(ref.removeprefix(prefix))
    return tuple(values)


def authenticated_login(repo: Path) -> str:
    proc = run_gh(repo, ["api", "user", "--jq", ".login"])
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip()
            or proc.stdout.strip()
            or "failed to resolve authenticated GitHub user",
        )
    return proc.stdout.strip()


def pr_heads(
    repo: Path,
    state: str,
    limit: int,
) -> tuple[frozenset[str], frozenset[str]]:
    login = authenticated_login(repo) if state == "merged" else ""
    proc = run_gh(
        repo,
        [
            "pr",
            "list",
            "--state",
            state,
            "--limit",
            str(limit),
            "--json",
            "headRefName,isCrossRepository,author",
        ],
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip()
            or proc.stdout.strip()
            or "failed to list pull requests",
        )
    payload = json.loads(proc.stdout)
    heads: set[str] = set()
    owned_heads: set[str] = set()
    for item in payload:
        head = str(item.get("headRefName") or "")
        if not head or item.get("isCrossRepository"):
            continue
        heads.add(head)
        author = item.get("author") or {}
        if login and author.get("login") == login:
            owned_heads.add(head)
    return frozenset(heads), frozenset(owned_heads)


def inspect_state(repo: Path, remote: str, limit: int) -> BranchState:
    if shutil.which("gh") is None:
        raise RuntimeError("gh command not found")
    merged_pr_heads, owned_merged_pr_heads = pr_heads(repo, "merged", limit)
    open_pr_heads, _ = pr_heads(repo, "open", limit)
    return BranchState(
        default_branch=resolve_default_branch(repo, remote=remote),
        current_branch=current_branch(repo),
        local_branches=local_branches(repo),
        remote_branches=remote_branches(repo, remote),
        merged_pr_heads=merged_pr_heads,
        owned_merged_pr_heads=owned_merged_pr_heads,
        open_pr_heads=open_pr_heads,
    )


def protected_reason(branch: str, state: BranchState) -> str:
    if branch == state.default_branch:
        return "default branch"
    if branch == state.current_branch:
        return "current branch"
    if branch in state.open_pr_heads:
        return "open pull request"
    return ""


def cleanup_branch(
    repo: Path,
    repo_label: str,
    *,
    target: str,
    branch: str,
    state: BranchState,
    remote: str,
    apply: bool,
    include_non_owner_remote: bool,
) -> BranchResult:
    reason = protected_reason(branch, state)
    if reason:
        return BranchResult(repo_label, target, branch, "skipped", reason)
    if branch not in state.merged_pr_heads:
        return BranchResult(
            repo_label,
            target,
            branch,
            "skipped",
            "no merged pull request",
        )
    if (
        target == "remote"
        and not include_non_owner_remote
        and branch not in state.owned_merged_pr_heads
    ):
        return BranchResult(
            repo_label,
            target,
            branch,
            "skipped",
            "merged pull request not owned by authenticated user",
        )
    if not apply:
        return BranchResult(
            repo_label,
            target,
            branch,
            "would-delete",
            "merged pull request",
        )

    if target == "local":
        proc = run_git(repo, ["branch", "-d", branch])
    else:
        proc = run_git(repo, ["push", remote, "--delete", branch])
    if proc.returncode != 0:
        return BranchResult(
            repo_label,
            target,
            branch,
            "failed",
            (proc.stderr or proc.stdout).strip(),
        )
    return BranchResult(repo_label, target, branch, "deleted", "merged pull request")


def pr_unavailable(message: str) -> bool:
    lowered = message.lower()
    return (
        "could not resolve to a repository" in lowered
        or "not a github repository" in lowered
        or "no remotes configured" in lowered
    )


def cleanup_repo(
    root: Path,
    repo_path: str,
    *,
    include_local: bool,
    include_remote: bool,
    include_non_owner_remote: bool,
    remote: str,
    apply: bool,
    limit: int,
) -> list[BranchResult]:
    repo = root if repo_path == "." else root / repo_path
    try:
        state = inspect_state(repo, remote, limit)
    except Exception as exc:
        status = "skipped" if pr_unavailable(str(exc)) else "failed"
        return [BranchResult(repo_path, "repo", "", status, str(exc))]

    results: list[BranchResult] = []
    if include_local:
        results.extend(
            cleanup_branch(
                repo,
                repo_path,
                target="local",
                branch=branch,
                state=state,
                remote=remote,
                apply=apply,
                include_non_owner_remote=include_non_owner_remote,
            )
            for branch in state.local_branches
        )
    if include_remote:
        results.extend(
            cleanup_branch(
                repo,
                repo_path,
                target="remote",
                branch=branch,
                state=state,
                remote=remote,
                apply=apply,
                include_non_owner_remote=include_non_owner_remote,
            )
            for branch in state.remote_branches
        )
    return results


def target_paths(root: Path, mode: str) -> list[str]:
    if mode == "one":
        return ["."]
    submodules = read_gitmodules_paths(root)
    if mode == "all":
        return submodules
    return [".", *submodules]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Clean up branches whose pull requests are already merged.",
    )
    parser.add_argument("mode", choices=("one", "all", "root-and-all"))
    parser.add_argument(
        "--apply",
        action="store_true",
        help="delete branches; default is dry-run",
    )
    parser.add_argument(
        "--local",
        dest="include_local",
        action="store_true",
        default=True,
        help="include local branches",
    )
    parser.add_argument(
        "--no-local",
        dest="include_local",
        action="store_false",
        help="exclude local branches",
    )
    parser.add_argument(
        "--remote",
        dest="include_remote",
        action="store_true",
        default=True,
        help="include remote branches",
    )
    parser.add_argument(
        "--no-remote",
        dest="include_remote",
        action="store_false",
        help="exclude remote branches",
    )
    parser.add_argument(
        "--include-non-owner-remote",
        action="store_true",
        help=(
            "include remote branch cleanup for merged pull requests"
            " not owned by the authenticated user"
        ),
    )
    parser.add_argument(
        "--remote-name",
        default="origin",
        help="remote name to inspect/delete (default: origin)",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=200,
        help="merged/open PR lookup limit (default: 200)",
    )
    parser.add_argument(
        "--jobs",
        type=positive_int,
        default=4,
        help="parallel workers for all modes (default: 4)",
    )
    parser.add_argument("--format", choices=("table", "tsv", "jsonl"), default="table")
    parser.add_argument(
        "--include-skipped",
        action="store_true",
        help="include skipped branches in the output",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    root = Path.cwd()
    paths = target_paths(root, args.mode)
    results, failures = run_parallel_with_progress(
        paths,
        lambda path: cleanup_repo(
            root,
            path,
            include_local=args.include_local,
            include_remote=args.include_remote,
            include_non_owner_remote=args.include_non_owner_remote,
            remote=args.remote_name,
            apply=args.apply,
            limit=args.limit,
        ),
        jobs=args.jobs,
        desc="branches",
        unit="repo",
    )
    rows = [row for repo_rows in results for row in repo_rows]
    rows.extend(
        BranchResult(failure.item, "repo", "", "failed", failure.message)
        for failure in failures
    )
    if not args.include_skipped:
        rows = [row for row in rows if row.status != "skipped"]
    rows.sort(key=lambda row: (row.repo, row.target, row.branch))
    print_records(rows, FIELDS, args.format)
    return 1 if any(row.status == "failed" for row in rows) else 0


if __name__ == "__main__":
    raise SystemExit(main())
