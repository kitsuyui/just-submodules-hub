from __future__ import annotations

import argparse
import json
import subprocess
import sys

from just_submodules_hub.gitmodules import managed_repo_slugs, read_gitmodules_paths
from just_submodules_hub.github_rulesets import (
    BASELINE_RULESET_NAME,
    candidate_legacy_rulesets,
    desired_ruleset_payload,
    find_ruleset_by_identifier,
    find_ruleset_by_name,
    parse_json_payload,
    parse_repo_metadata,
    summarize_classic_branch_protection,
    summarize_legacy_rulesets,
    summarize_ruleset_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bulk operations for default branch baseline protection.")
    parser.add_argument(
        "action",
        choices=("status-all", "apply-all", "cleanup-rulesets-all", "cleanup-classic-all"),
    )
    parser.add_argument("visibility", nargs="?", default="public", choices=("public", "private", "all"))
    return parser.parse_args()


def run_gh(*args: str) -> str:
    proc = subprocess.run(
        ["gh", *args],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"gh command failed: {' '.join(args)}")
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
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or f"gh command failed: {' '.join(args)}")
    parsed = json.loads(proc.stdout)
    if not isinstance(parsed, dict):
        raise RuntimeError("GitHub API response must be a JSON object")
    return parsed


def load_repo_metadata(repo: str) -> dict:
    return json.loads(run_gh("repo", "view", repo, "--json", "nameWithOwner,visibility,defaultBranchRef"))


def load_effective_rules(repo: str, branch: str) -> list[dict]:
    return parse_json_payload(run_gh("api", f"repos/{repo}/rules/branches/{branch}"))


def load_rulesets(repo: str) -> list[dict]:
    summaries = parse_json_payload(run_gh("api", f"repos/{repo}/rulesets"))
    hydrated: list[dict] = []
    for item in summaries:
        ruleset_id = item.get("id")
        if ruleset_id is None:
            continue
        detail = json.loads(run_gh("api", f"repos/{repo}/rulesets/{ruleset_id}"))
        if isinstance(detail, dict):
            hydrated.append(detail)
    return hydrated


def load_classic_branch_protection(repo: str, branch: str) -> dict | None:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}/branches/{branch}/protection"],
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode == 0:
        payload = json.loads(proc.stdout)
        if isinstance(payload, dict):
            return payload
        raise RuntimeError("classic branch protection payload must be an object")

    combined = "\n".join(part for part in (proc.stdout.strip(), proc.stderr.strip()) if part).lower()
    if "branch not protected" in combined:
        return None
    raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "failed to load classic branch protection")


def write_json(data: dict) -> None:
    sys.stdout.write(json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True))
    sys.stdout.write("\n")


def managed_repositories(visibility: str) -> list[tuple[str, dict]]:
    repos = managed_repo_slugs(read_gitmodules_paths("."))
    selected: list[tuple[str, dict]] = []
    for repo in repos:
        metadata = load_repo_metadata(repo)
        parsed = parse_repo_metadata(json.dumps(metadata))
        if visibility != "all" and parsed.visibility != visibility:
            continue
        selected.append((repo, metadata))
    return selected


def status_all(visibility: str) -> int:
    entries = []
    for repo, raw_metadata in managed_repositories(visibility):
        metadata = parse_repo_metadata(json.dumps(raw_metadata))
        effective_rules = load_effective_rules(repo, metadata.default_branch)
        rulesets = load_rulesets(repo)
        classic = load_classic_branch_protection(repo, metadata.default_branch)
        entries.append(
            {
                "repo": repo,
                "visibility": metadata.visibility,
                "ruleset_status": summarize_ruleset_status(metadata, effective_rules, rulesets),
                "legacy_rulesets": summarize_legacy_rulesets(metadata, rulesets)["legacy_rulesets"],
                "classic_protection": summarize_classic_branch_protection(metadata, classic, effective_rules),
            }
        )

    write_json(
        {
            "action": "status-all",
            "visibility": visibility,
            "repos": entries,
        }
    )
    return 0


def apply_all(visibility: str) -> int:
    results = []
    for repo, raw_metadata in managed_repositories(visibility):
        metadata = parse_repo_metadata(json.dumps(raw_metadata))
        rulesets = load_rulesets(repo)
        managed_ruleset = find_ruleset_by_name(rulesets)
        payload = desired_ruleset_payload(metadata.default_branch)
        if managed_ruleset and managed_ruleset.get("id") is not None:
            result = run_gh_with_json_input(
                ["api", "--method", "PUT", f"repos/{repo}/rulesets/{managed_ruleset['id']}"],
                payload,
            )
            results.append({"repo": repo, "action": "updated", "ruleset_id": result.get("id", managed_ruleset["id"])})
            continue

        result = run_gh_with_json_input(
            ["api", "--method", "POST", f"repos/{repo}/rulesets"],
            payload,
        )
        results.append({"repo": repo, "action": "created", "ruleset_id": result.get("id")})

    write_json({"action": "apply-all", "visibility": visibility, "results": results})
    return 0


def cleanup_rulesets_all(visibility: str) -> int:
    results = []
    for repo, raw_metadata in managed_repositories(visibility):
        metadata = parse_repo_metadata(json.dumps(raw_metadata))
        rulesets = load_rulesets(repo)
        summary = summarize_legacy_rulesets(metadata, rulesets)
        for item in summary["legacy_rulesets"]:
            if item["deletable"]:
                target = find_ruleset_by_identifier(candidate_legacy_rulesets(metadata, rulesets), str(item["id"]))
                if not target:
                    continue
                run_gh("api", "--method", "DELETE", f"repos/{repo}/rulesets/{target['id']}")
                results.append({"repo": repo, "action": "deleted", "ruleset_id": target["id"], "name": target["name"]})
            else:
                results.append(
                    {
                        "repo": repo,
                        "action": "skipped",
                        "name": item["name"],
                        "reason": "manual_action_required",
                        "uncovered_rule_types": item["uncovered_rule_types"],
                    }
                )

    write_json({"action": "cleanup-rulesets-all", "visibility": visibility, "results": results})
    return 0


def cleanup_classic_all(visibility: str) -> int:
    results = []
    for repo, raw_metadata in managed_repositories(visibility):
        metadata = parse_repo_metadata(json.dumps(raw_metadata))
        effective_rules = load_effective_rules(repo, metadata.default_branch)
        protection = load_classic_branch_protection(repo, metadata.default_branch)
        summary = summarize_classic_branch_protection(metadata, protection, effective_rules)
        if not summary["classic_branch_protection_found"]:
            continue
        if summary["deletable"]:
            run_gh("api", "--method", "DELETE", f"repos/{repo}/branches/{metadata.default_branch}/protection")
            results.append({"repo": repo, "action": "deleted", "deleted": "classic_branch_protection"})
        else:
            results.append(
                {
                    "repo": repo,
                    "action": "skipped",
                    "reason": "manual_action_required",
                    "uncovered_settings": summary["uncovered_settings"],
                }
            )

    write_json({"action": "cleanup-classic-all", "visibility": visibility, "results": results})
    return 0


def main() -> int:
    args = parse_args()
    if args.action == "status-all":
        return status_all(args.visibility)
    if args.action == "apply-all":
        return apply_all(args.visibility)
    if args.action == "cleanup-rulesets-all":
        return cleanup_rulesets_all(args.visibility)
    return cleanup_classic_all(args.visibility)


if __name__ == "__main__":
    raise SystemExit(main())
