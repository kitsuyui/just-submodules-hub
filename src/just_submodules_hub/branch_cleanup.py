"""Clean up branches whose pull requests are already merged."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from just_submodules_hub.default_branch import resolve_default_branch
from just_submodules_hub.github_cli import run_gh as run_gh_command
from just_submodules_hub.gitmodules import read_gitmodules_paths
from just_submodules_hub.submodule_batch import (
    positive_int,
    print_records,
    run_parallel_with_progress,
)

FIELDS = ("repo", "target", "branch", "status", "reason")


@dataclass(frozen=True)
class BranchResult:
    """A single branch-cleanup outcome for one (repo, target, branch) triple."""

    repo: str
    target: str
    branch: str
    status: str
    reason: str


@dataclass(frozen=True)
class BranchState:
    """Captured branch and PR state for a repository."""

    default_branch: str
    current_branch: str
    local_branches: tuple[str, ...]
    remote_branches: tuple[str, ...]
    merged_pr_heads: frozenset[str]
    owned_merged_pr_heads: frozenset[str]
    open_pr_heads: frozenset[str]
    worktree_branches: frozenset[str] = frozenset()


def run_git(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a git command in *repo* and return the CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=str(repo),
        text=True,
        capture_output=True,
        check=False,
    )


def run_gh(repo: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a gh command in *repo* and return the CompletedProcess."""
    return run_gh_command(args, cwd=repo)


def lines(proc: subprocess.CompletedProcess[str]) -> tuple[str, ...]:
    """Return non-empty stripped lines from the stdout of *proc*."""
    return tuple(line.strip() for line in proc.stdout.splitlines() if line.strip())


def current_branch(repo: Path) -> str:
    """Return the current branch name, or empty string on failure."""
    proc = run_git(repo, ["branch", "--show-current"])
    return proc.stdout.strip() if proc.returncode == 0 else ""


def local_branches(repo: Path) -> tuple[str, ...]:
    """Return all local branch names in *repo*."""
    proc = run_git(repo, ["for-each-ref", "--format=%(refname:short)", "refs/heads"])
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "failed to list local branches")
    return lines(proc)


def remote_branches(repo: Path, remote: str) -> tuple[str, ...]:
    """Return all branch names on *remote* for *repo*."""
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


def linked_worktree_branches(repo: Path) -> frozenset[str]:
    """Return branches checked out in any worktree of *repo*.

    Includes the main worktree and all linked worktrees. ``git branch -d``
    and ``-D`` both refuse to delete a branch that is checked out in any
    worktree, so callers should treat these as protected to avoid noisy
    failures.
    """
    proc = run_git(repo, ["worktree", "list", "--porcelain"])
    if proc.returncode != 0:
        return frozenset()
    branches: set[str] = set()
    prefix = "refs/heads/"
    for line in proc.stdout.splitlines():
        if line.startswith("branch "):
            ref = line.removeprefix("branch ").strip()
            if ref.startswith(prefix):
                branches.add(ref.removeprefix(prefix))
    return frozenset(branches)


def authenticated_login(repo: Path) -> str:
    """Return the login of the authenticated GitHub user."""
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
    """Return (all_heads, owned_heads) for PRs in the given *state* up to *limit*."""
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
    """Inspect the full branch and PR state for *repo*."""
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
        worktree_branches=linked_worktree_branches(repo),
    )


def protected_reason(branch: str, state: BranchState) -> str:
    """Return a non-empty reason string if *branch* must not be deleted."""
    if branch == state.default_branch:
        return "default branch"
    if branch == state.current_branch:
        return "current branch"
    if branch in state.worktree_branches:
        return "checked out in another worktree"
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
    """Evaluate and optionally delete one branch."""
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
        if proc.returncode != 0:
            # Squash-merge / rebase-merge case: ``git branch -d`` refuses
            # because the merged PR appears on the default branch as a
            # different commit. The branch was already verified to be in
            # ``state.merged_pr_heads`` above, so the work is preserved on
            # the remote and ``-D`` is safe.
            force_proc = run_git(repo, ["branch", "-D", branch])
            if force_proc.returncode == 0:
                return BranchResult(
                    repo_label,
                    target,
                    branch,
                    "deleted",
                    "merged pull request (force-deleted; squash/rebase)",
                )
            proc = force_proc
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
    """Return True if the error message indicates a non-GitHub repo."""
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
    """Clean up merged-PR branches for a single repository."""
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
    """Return the list of repo paths to process for the given *mode*."""
    if mode == "one":
        return ["."]
    submodules = read_gitmodules_paths(root)
    if mode == "all":
        return submodules
    return [".", *submodules]


def build_parser() -> argparse.ArgumentParser:
    """Return the argument parser for the branch-cleanup command."""
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


def main(argv: list[str] | None = None) -> int:
    """Clean up merged-PR branches and print a report."""
    args = build_parser().parse_args(argv)
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
