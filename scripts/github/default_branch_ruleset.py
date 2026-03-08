from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from just_submodules_hub.github_rulesets import (
    BASELINE_RULESET_NAME,
    candidate_legacy_rulesets,
    desired_ruleset_payload,
    find_ruleset_by_name,
    find_ruleset_by_identifier,
    parse_json_payload,
    parse_repo_metadata,
    summarize_classic_branch_protection,
    summarize_legacy_rulesets,
    summarize_ruleset_status,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Inspect or upsert a baseline ruleset for a repository default branch."
    )
    parser.add_argument(
        "action",
        choices=(
            "status",
            "apply",
            "legacy-status",
            "delete-if-redundant",
            "classic-status",
            "classic-delete-if-redundant",
        ),
    )
    parser.add_argument("repo", help="Repository slug such as owner/name")
    parser.add_argument("identifier", nargs="?", help="Legacy ruleset id or name for delete-if-redundant")
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
            hydrated.append(item)
            continue
        detail = json.loads(run_gh("api", f"repos/{repo}/rulesets/{ruleset_id}"))
        if isinstance(detail, dict):
            hydrated.append(detail)
        else:
            hydrated.append(item)
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


def status(repo: str) -> int:
    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    effective_rules = load_effective_rules(repo, metadata.default_branch)
    rulesets = load_rulesets(repo)
    write_json(summarize_ruleset_status(metadata, effective_rules, rulesets))
    return 0


def apply(repo: str) -> int:
    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    rulesets = load_rulesets(repo)
    managed_ruleset = find_ruleset_by_name(rulesets)
    payload = desired_ruleset_payload(metadata.default_branch)

    with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)
        handle.write("\n")
        payload_path = Path(handle.name)

    try:
        if managed_ruleset and managed_ruleset.get("id") is not None:
            ruleset_id = str(managed_ruleset["id"])
            response = run_gh(
                "api",
                "--method",
                "PUT",
                f"repos/{repo}/rulesets/{ruleset_id}",
                "--input",
                str(payload_path),
            )
            result = json.loads(response)
            write_json(
                {
                    "action": "updated",
                    "repo": metadata.name_with_owner,
                    "ruleset_id": result.get("id", managed_ruleset["id"]),
                    "ruleset_name": BASELINE_RULESET_NAME,
                    "default_branch": metadata.default_branch,
                    "visibility": metadata.visibility,
                }
            )
            return 0

        response = run_gh(
            "api",
            "--method",
            "POST",
            f"repos/{repo}/rulesets",
            "--input",
            str(payload_path),
        )
        result = json.loads(response)
        write_json(
            {
                "action": "created",
                "repo": metadata.name_with_owner,
                "ruleset_id": result.get("id"),
                "ruleset_name": BASELINE_RULESET_NAME,
                "default_branch": metadata.default_branch,
                "visibility": metadata.visibility,
            }
        )
        return 0
    finally:
        payload_path.unlink(missing_ok=True)


def legacy_status(repo: str) -> int:
    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    rulesets = load_rulesets(repo)
    write_json(summarize_legacy_rulesets(metadata, rulesets))
    return 0


def delete_if_redundant(repo: str, identifier: str | None) -> int:
    if not identifier:
        raise ValueError("legacy ruleset identifier is required")

    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    rulesets = load_rulesets(repo)
    legacy_rulesets = candidate_legacy_rulesets(metadata, rulesets)
    target = find_ruleset_by_identifier(legacy_rulesets, identifier)
    if not target:
        raise ValueError(f"legacy ruleset not found for identifier: {identifier}")

    summary = summarize_legacy_rulesets(metadata, rulesets)
    target_summary = find_ruleset_by_identifier(summary["legacy_rulesets"], identifier)
    if not target_summary:
        raise ValueError(f"legacy ruleset summary not found for identifier: {identifier}")
    if not target_summary.get("deletable"):
        raise RuntimeError(
            "legacy ruleset is not redundant; manual review required for rule types: "
            + ", ".join(target_summary.get("uncovered_rule_types", []))
        )

    run_gh("api", "--method", "DELETE", f"repos/{repo}/rulesets/{target['id']}")
    write_json(
        {
            "action": "deleted",
            "repo": metadata.name_with_owner,
            "ruleset_id": target.get("id"),
            "ruleset_name": target.get("name"),
            "default_branch": metadata.default_branch,
        }
    )
    return 0


def classic_status(repo: str) -> int:
    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    effective_rules = load_effective_rules(repo, metadata.default_branch)
    protection = load_classic_branch_protection(repo, metadata.default_branch)
    write_json(summarize_classic_branch_protection(metadata, protection, effective_rules))
    return 0


def classic_delete_if_redundant(repo: str) -> int:
    metadata = parse_repo_metadata(json.dumps(load_repo_metadata(repo)))
    effective_rules = load_effective_rules(repo, metadata.default_branch)
    protection = load_classic_branch_protection(repo, metadata.default_branch)
    summary = summarize_classic_branch_protection(metadata, protection, effective_rules)
    if not summary["classic_branch_protection_found"]:
        raise RuntimeError("classic branch protection not found")
    if not summary["deletable"]:
        raise RuntimeError(
            "classic branch protection is not redundant; manual review required for settings: "
            + ", ".join(summary["uncovered_settings"])
        )

    run_gh("api", "--method", "DELETE", f"repos/{repo}/branches/{metadata.default_branch}/protection")
    write_json(
        {
            "action": "deleted",
            "repo": metadata.name_with_owner,
            "default_branch": metadata.default_branch,
            "deleted": "classic_branch_protection",
        }
    )
    return 0


def main() -> int:
    args = parse_args()
    if args.action == "status":
        return status(args.repo)
    if args.action == "apply":
        return apply(args.repo)
    if args.action == "legacy-status":
        return legacy_status(args.repo)
    if args.action == "delete-if-redundant":
        return delete_if_redundant(args.repo, args.identifier)
    if args.action == "classic-status":
        return classic_status(args.repo)
    return classic_delete_if_redundant(args.repo)


if __name__ == "__main__":
    raise SystemExit(main())
