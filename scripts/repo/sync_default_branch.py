#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from tqdm import tqdm


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


def as_bool(raw: str, default: bool) -> bool:
    if raw == "":
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def run(cmd: List[str], cwd: Path | None = None) -> str:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout).strip() or "command failed")
    return proc.stdout.strip()


def repo_display_name(repo_path: str) -> str:
    prefix = "repo/github.com/"
    if repo_path.startswith(prefix):
        return repo_path[len(prefix) :]
    return repo_path


def parse_repo_paths() -> List[str]:
    out = run(["git", "config", "-f", ".gitmodules", "--get-regexp", r"^submodule\..*\.path$"])
    paths: List[str] = []
    for line in out.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[1]:
            paths.append(parts[1])
    return paths


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

        repo_owner = payload.get("data", {}).get("repositoryOwner")
        if repo_owner is None:
            raise RuntimeError(f"repository owner not found: {owner}")

        repos = repo_owner["repositories"]
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


def build_sync_targets(paths: Iterable[str], prefilter: bool, bar: tqdm) -> Tuple[List[str], int]:
    path_list = list(paths)
    if not prefilter:
        return path_list, 0

    owners = sorted({repo_display_name(p).split("/", 1)[0] for p in path_list})
    heads: Dict[str, Tuple[str, str]] = {}

    for owner in owners:
        heads.update(fetch_owner_default_heads(owner, bar))

    targets: List[str] = []
    skipped = 0

    for repo_path in path_list:
        slug = repo_display_name(repo_path)
        remote = heads.get(slug)
        if not remote:
            targets.append(repo_path)
            continue
        remote_branch, remote_oid = remote
        local_branch, local_oid = local_head(repo_path)
        if local_branch == remote_branch and local_oid == remote_oid:
            skipped += 1
            continue
        targets.append(repo_path)

    return targets, skipped


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


def main() -> int:
    if len(sys.argv) < 2:
        print("action is required", file=sys.stderr)
        return 2

    action = sys.argv[1]
    verbose = as_bool(os.getenv("SYNC_VERBOSE", "0"), False)
    prefilter = as_bool(os.getenv("SYNC_PREFILTER_REMOTE_HEADS", "1"), True)

    jobs_raw = os.getenv("SYNC_JOBS", "4").strip()
    jobs = 4
    if jobs_raw.isdigit() and int(jobs_raw) > 0:
        jobs = int(jobs_raw)

    try:
        if action == "one":
            if len(sys.argv) < 3:
                print("repo path is required", file=sys.stderr)
                return 2
            result = sync_one(sys.argv[2])
            print_result(result, verbose)
            return 0

        if action == "all":
            paths = parse_repo_paths()
            if not paths:
                print("No submodule paths found in .gitmodules")
                return 0
            owner_count = len({repo_display_name(p).split("/", 1)[0] for p in paths}) if prefilter else 0
            with tqdm(
                total=len(paths) + owner_count,
                desc="sync-all",
                unit="task",
                leave=False,
                dynamic_ncols=True,
                bar_format=TQDM_BAR_FORMAT,
            ) as bar:
                targets, skipped = build_sync_targets(paths, prefilter, bar)
                if not targets:
                    print("All submodules are up to date.")
                    return 0
                code, changed_count = sync_all(targets, jobs, verbose, bar)

            if code == 0 and changed_count == 0 and not verbose:
                print("All submodules are up to date.")
            return code

        print(f"Unknown sync action: {action}", file=sys.stderr)
        return 2
    except RuntimeError as err:
        print(str(err), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
