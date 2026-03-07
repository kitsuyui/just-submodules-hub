from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from tqdm import tqdm

from .gitmodules import read_gitmodules_paths
from .repo_paths import repo_display_name, repo_owner
from .shell import run


GRAPHQL_QUERY = """
query($owner: String!, $cursor: String) {
  repositoryOwner(login: $owner) {
    repositories(first: 100, after: $cursor, ownerAffiliations: OWNER) {
      nodes {
        name
        defaultBranchRef {
          name
          target {
            ... on Commit {
              oid
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

TQDM_BAR_FORMAT = "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"


@dataclass
class SyncResult:
    repo_path: str
    default_branch: str
    switched: bool
    updated: bool
    skipped: bool = False
    skip_reason: str = ""


def positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer") from exc
    if value < 1:
        raise argparse.ArgumentTypeError("must be >= 1")
    return value


def parse_repo_paths(repo_root: Path | str = ".") -> List[str]:
    return read_gitmodules_paths(repo_root)


def gh_graphql(owner: str, cursor: str | None) -> dict:
    cmd = ["gh", "api", "graphql", "-F", f"owner={owner}", "-f", f"query={GRAPHQL_QUERY}"]
    if cursor:
        cmd.extend(["-F", f"cursor={cursor}"])
    out = run(cmd)
    return json.loads(out)


def fetch_owner_default_heads(owner: str, bar: tqdm) -> Dict[str, Tuple[str, str]]:
    cursor: str | None = None
    found: Dict[str, Tuple[str, str]] = {}

    while True:
        payload = gh_graphql(owner, cursor)
        bar.update(1)

        repo_owner_payload = payload.get("data", {}).get("repositoryOwner")
        if repo_owner_payload is None:
            raise RuntimeError(f"repository owner not found: {owner}")

        repos = repo_owner_payload["repositories"]
        for node in repos.get("nodes", []):
            default_ref = node.get("defaultBranchRef")
            if not default_ref:
                continue
            target = default_ref.get("target") or {}
            oid = target.get("oid")
            name = default_ref.get("name")
            repo_name = node.get("name")
            if not oid or not name or not repo_name:
                continue
            found[f"{owner}/{repo_name}"] = (name, oid)

        page_info = repos.get("pageInfo", {})
        if not page_info.get("hasNextPage"):
            break

        cursor = page_info.get("endCursor")
        if not cursor:
            break
        bar.total = (bar.total or 0) + 1
        bar.refresh()

    return found


def local_head(repo_path: str) -> Tuple[str, str]:
    cwd = Path(repo_path)
    branch = "DETACHED"
    try:
        branch = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd)
    except Exception:
        pass
    oid = run(["git", "rev-parse", "HEAD"], cwd=cwd)
    return branch, oid


def build_sync_targets(paths: Iterable[str], prefilter: bool, bar: tqdm) -> List[str]:
    path_list = list(paths)
    if not prefilter:
        return path_list

    owners = sorted({repo_owner(path) for path in path_list})
    heads: Dict[str, Tuple[str, str]] = {}

    for owner in owners:
        heads.update(fetch_owner_default_heads(owner, bar))

    targets: List[str] = []

    for repo_path in path_list:
        slug = repo_display_name(repo_path)
        remote = heads.get(slug)
        if not remote:
            targets.append(repo_path)
            continue
        remote_branch, remote_oid = remote
        local_branch, local_oid = local_head(repo_path)
        if local_branch == remote_branch and local_oid == remote_oid:
            bar.update(1)
            continue
        targets.append(repo_path)

    return targets


def resolve_default_branch(repo_path: str) -> str:
    cwd = Path(repo_path)
    try:
        out = run(["git", "symbolic-ref", "--short", "refs/remotes/origin/HEAD"], cwd=cwd)
        if out.startswith("origin/"):
            return out[len("origin/") :]
        if out:
            return out
    except Exception:
        pass

    show = run(["git", "remote", "show", "origin"], cwd=cwd)
    for line in show.splitlines():
        if "HEAD branch:" in line:
            return line.split("HEAD branch:", 1)[1].strip()
    raise RuntimeError(f"Could not resolve default branch for {repo_path}")


def sync_one(repo_path: str) -> SyncResult:
    cwd = Path(repo_path)
    if not (cwd / ".git").exists():
        raise RuntimeError(f"Repository path not found: {repo_path}")

    current_branch = "DETACHED"
    try:
        current_branch = run(["git", "symbolic-ref", "--quiet", "--short", "HEAD"], cwd=cwd)
    except Exception:
        pass

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
    default_branch = resolve_default_branch(repo_path)

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
    if result.skipped:
        print(f"{name}: skipped ({result.skip_reason})")
        return False

    if not result.switched and not result.updated:
        if verbose:
            print(f"{name}: up-to-date")
        return False

    parts: List[str] = []
    if result.switched:
        parts.append(f"switched-to:{result.default_branch}")
    if result.updated:
        parts.append("updated-to:latest")
    print(f"{name}: {' '.join(parts)}")
    return True


def sync_all(paths: List[str], jobs: int, verbose: bool, bar: tqdm) -> Tuple[int, int]:
    failures: List[Tuple[str, str]] = []
    results: List[SyncResult] = []

    with ThreadPoolExecutor(max_workers=jobs) as pool:
        future_map = {pool.submit(sync_one, p): p for p in paths}
        for fut in as_completed(future_map):
            repo_path = future_map[fut]
            try:
                results.append(fut.result())
            except Exception as exc:
                failures.append((repo_path, str(exc)))
            finally:
                bar.update(1)

    changed_count = 0
    for result in sorted(results, key=lambda r: r.repo_path):
        if print_result(result, verbose):
            changed_count += 1

    if failures:
        for repo_path, msg in failures:
            print(f"{repo_display_name(repo_path)}: {msg}", file=sys.stderr)
        print("One or more repositories failed to sync", file=sys.stderr)
        return 1, changed_count
    return 0, changed_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sync submodules to default branches")
    subparsers = parser.add_subparsers(dest="action", required=True)

    one = subparsers.add_parser("one", help="sync one repository")
    one.add_argument("repo_path", help="repository path (e.g. repo/github.com/owner/repo)")
    one.add_argument("--verbose", action="store_true", help="show up-to-date repositories")

    all_cmd = subparsers.add_parser("all", help="sync all repositories from .gitmodules")
    all_cmd.add_argument("--jobs", type=positive_int, default=4, help="parallel workers (default: 4)")
    all_cmd.add_argument("--verbose", action="store_true", help="show up-to-date repositories")
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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    action = args.action

    try:
        if action == "one":
            result = sync_one(args.repo_path)
            print_result(result, args.verbose)
            return 0

        if action == "all":
            paths = parse_repo_paths()
            if not paths:
                print("No submodule paths found in .gitmodules")
                return 0
            owner_count = len({repo_owner(path) for path in paths}) if args.prefilter else 0
            with tqdm(
                total=len(paths) + owner_count,
                desc="sync-all",
                unit="task",
                leave=False,
                dynamic_ncols=True,
                bar_format=TQDM_BAR_FORMAT,
            ) as bar:
                targets = build_sync_targets(paths, args.prefilter, bar)
                if not targets:
                    print("All submodules are up to date.")
                    return 0
                code, changed_count = sync_all(targets, args.jobs, args.verbose, bar)

            if code == 0 and changed_count == 0 and not args.verbose:
                print("All submodules are up to date.")
            return code

        print(f"Unknown sync action: {action}", file=sys.stderr)
        return 2
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 1
