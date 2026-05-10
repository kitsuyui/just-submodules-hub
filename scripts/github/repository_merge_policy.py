from __future__ import annotations

import argparse
import json
import subprocess
import sys

from tqdm import tqdm

from just_submodules_hub.github_merge_policy import (
    MERGE_METHODS,
    MERGE_POLICY_FIELDS,
    merge_method_patch_payload,
    summarize_merge_method,
)
from just_submodules_hub.gitmodules import managed_repo_slugs, read_gitmodules_paths

TQDM_BAR_FORMAT = (
    "{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or apply repository merge method policy.",
    )
    parser.add_argument(
        "action",
        choices=(
            "status",
            "enable",
            "disable",
            "status-all",
            "enable-all",
            "disable-all",
        ),
    )
    parser.add_argument("method", choices=MERGE_METHODS)
    parser.add_argument(
        "target",
        nargs="?",
        help="Repository slug or visibility for *-all actions",
    )
    return parser.parse_args()


def run_gh(*args: str) -> str:
    proc = subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip()
            or proc.stdout.strip()
            or f"gh command failed: {' '.join(args)}",
        )
    return proc.stdout


def run_gh_with_json_input(args: list[str], payload: dict) -> dict:
    proc = subprocess.run(
        ["gh", *args, "--input", "-"],
        text=True,
        input=json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            proc.stderr.strip()
            or proc.stdout.strip()
            or f"gh command failed: {' '.join(args)}",
        )
    parsed = json.loads(proc.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("GitHub API response must be a JSON object")
    return parsed


def load_repo_metadata(repo: str) -> dict:
    payload = json.loads(run_gh("repo", "view", repo, "--json", MERGE_POLICY_FIELDS))
    if not isinstance(payload, dict):
        raise RuntimeError("repository metadata payload must be an object")
    return payload


def write_json(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True))
    sys.stdout.write("\n")


def supports_merge_policy(repo: str) -> bool:
    return not repo.endswith(".wiki")


def candidate_repositories() -> list[str]:
    return [
        repo
        for repo in managed_repo_slugs(read_gitmodules_paths("."))
        if supports_merge_policy(repo)
    ]


def repo_name(payload: dict) -> str:
    value = payload.get("nameWithOwner")
    if not isinstance(value, str) or not value:
        raise RuntimeError("repository metadata missing nameWithOwner")
    return value


def repo_visibility(payload: dict) -> str:
    value = payload.get("visibility")
    if not isinstance(value, str) or not value:
        raise RuntimeError("repository metadata missing visibility")
    return value.lower()


def summarize_method_payload(method: str, payload: dict) -> dict:
    return summarize_merge_method(
        repo_name(payload),
        repo_visibility(payload),
        method,
        payload,
    )


def status(method: str, repo: str) -> int:
    write_json(summarize_method_payload(method, load_repo_metadata(repo)))
    return 0


def set_method(method: str, repo: str, enabled: bool) -> int:
    before = load_repo_metadata(repo)
    result = run_gh_with_json_input(
        ["api", "--method", "PATCH", f"repos/{repo}"],
        merge_method_patch_payload(method, enabled),
    )
    after = result if "squashMergeAllowed" in result else load_repo_metadata(repo)
    action = "enabled" if enabled else "disabled"
    write_json(
        {
            "action": action,
            "repo": repo_name(before),
            "visibility": repo_visibility(before),
            "method": method,
            "before": summarize_method_payload(method, before),
            "after": summarize_method_payload(method, after),
        },
    )
    return 0


def validate_visibility(visibility: str) -> str:
    if visibility not in {"public", "private", "all"}:
        raise ValueError("visibility must be one of: public, private, all")
    return visibility


def build_progress_bar(action: str, total: int) -> tqdm:
    return tqdm(
        total=total,
        desc=action,
        unit="repo",
        leave=False,
        dynamic_ncols=True,
        bar_format=TQDM_BAR_FORMAT,
        file=sys.stderr,
    )


def managed_repositories(
    visibility: str,
    bar: tqdm | None = None,
) -> list[tuple[str, dict]]:
    selected: list[tuple[str, dict]] = []
    for repo in candidate_repositories():
        metadata = load_repo_metadata(repo)
        if bar is not None:
            bar.update(1)
        if visibility != "all" and repo_visibility(metadata) != visibility:
            continue
        selected.append((repo, metadata))
    return selected


def status_all(method: str, visibility: str) -> int:
    entries = []
    candidates = candidate_repositories()
    with build_progress_bar(f"{method} status-all", len(candidates)) as bar:
        repos = managed_repositories(visibility, bar)
        for _repo, metadata in repos:
            entries.append(summarize_method_payload(method, metadata))

    write_json(
        {
            "action": "status-all",
            "method": method,
            "visibility": visibility,
            "repos": entries,
        },
    )
    return 0


def set_method_all(method: str, visibility: str, enabled: bool) -> int:
    results = []
    candidates = candidate_repositories()
    action = "enable-all" if enabled else "disable-all"
    result_action = "enabled" if enabled else "disabled"
    with build_progress_bar(f"{method} {action}", len(candidates)) as bar:
        repos = managed_repositories(visibility, bar)
        bar.total += len(repos)
        bar.refresh()
        for repo, metadata in repos:
            result = run_gh_with_json_input(
                ["api", "--method", "PATCH", f"repos/{repo}"],
                merge_method_patch_payload(method, enabled),
            )
            after = (
                result if "squashMergeAllowed" in result else load_repo_metadata(repo)
            )
            results.append(
                {
                    "repo": repo_name(metadata),
                    "action": result_action,
                    "method": method,
                    "before": summarize_method_payload(method, metadata),
                    "after": summarize_method_payload(method, after),
                },
            )
            bar.update(1)

    write_json(
        {
            "action": action,
            "method": method,
            "visibility": visibility,
            "results": results,
        },
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.action == "status":
        if args.target is None:
            raise ValueError("repo is required for status")
        return status(args.method, args.target)
    if args.action == "enable":
        if args.target is None:
            raise ValueError("repo is required for enable")
        return set_method(args.method, args.target, True)
    if args.action == "disable":
        if args.target is None:
            raise ValueError("repo is required for disable")
        return set_method(args.method, args.target, False)

    visibility = validate_visibility(args.target or "public")
    if args.action == "status-all":
        return status_all(args.method, visibility)
    if args.action == "enable-all":
        return set_method_all(args.method, visibility, True)
    return set_method_all(args.method, visibility, False)


if __name__ == "__main__":
    raise SystemExit(main())
