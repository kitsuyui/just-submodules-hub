from __future__ import annotations

import json
from dataclasses import dataclass
from fnmatch import fnmatch


BASELINE_RULESET_NAME = "default-branch-baseline"
BASELINE_RULE_TYPES = ("pull_request", "non_fast_forward", "deletion")
BASELINE_PULL_REQUEST_PARAMETERS = {
    "required_approving_review_count": 0,
    "dismiss_stale_reviews_on_push": False,
    "require_code_owner_review": False,
    "require_last_push_approval": False,
    "required_review_thread_resolution": False,
}


@dataclass(frozen=True)
class RepoMetadata:
    name_with_owner: str
    visibility: str
    default_branch: str


def parse_repo_metadata(payload: str) -> RepoMetadata:
    item = json.loads(payload)
    default_branch = item.get("defaultBranchRef", {}).get("name")
    name_with_owner = item.get("nameWithOwner")
    visibility = item.get("visibility", "").lower()
    if not name_with_owner or not default_branch or not visibility:
        raise ValueError("repository metadata payload is incomplete")
    return RepoMetadata(
        name_with_owner=name_with_owner,
        visibility=visibility,
        default_branch=default_branch,
    )


def parse_json_payload(payload: str) -> list[dict]:
    parsed = json.loads(payload)
    if not isinstance(parsed, list):
        raise ValueError("payload must be a JSON array")
    return [item for item in parsed if isinstance(item, dict)]


def desired_ruleset_payload(default_branch: str) -> dict:
    return {
        "name": BASELINE_RULESET_NAME,
        "target": "branch",
        "enforcement": "active",
        "conditions": {
            "ref_name": {
                "include": [f"refs/heads/{default_branch}"],
                "exclude": [],
            }
        },
        "rules": [
            {
                "type": "pull_request",
                "parameters": dict(BASELINE_PULL_REQUEST_PARAMETERS),
            },
            {
                "type": "non_fast_forward",
            },
            {
                "type": "deletion",
            },
        ],
    }


def effective_rule_types(effective_rules: list[dict]) -> list[str]:
    return sorted({str(item.get("type")) for item in effective_rules if item.get("type")})


def find_ruleset_by_name(rulesets: list[dict], name: str = BASELINE_RULESET_NAME) -> dict | None:
    for item in rulesets:
        if item.get("name") == name:
            return item
    return None


def rules_by_type(rules: list[dict]) -> dict[str, dict]:
    typed: dict[str, dict] = {}
    for item in rules:
        rule_type = item.get("type")
        if isinstance(rule_type, str):
            typed[rule_type] = item
    return typed


def pull_request_parameters_match(rule: dict | None) -> bool:
    if not rule:
        return False
    parameters = rule.get("parameters")
    if not isinstance(parameters, dict):
        return False
    for key, expected in BASELINE_PULL_REQUEST_PARAMETERS.items():
        if parameters.get(key) != expected:
            return False
    return True


def extract_rules(ruleset: dict | None) -> list[dict]:
    if not isinstance(ruleset, dict):
        return []
    raw_rules = ruleset.get("rules", [])
    if not isinstance(raw_rules, list):
        return []
    return [item for item in raw_rules if isinstance(item, dict)]


def ref_includes_default_branch(ruleset: dict, default_branch: str) -> bool:
    if ruleset.get("target") != "branch":
        return False
    if ruleset.get("enforcement") != "active":
        return False

    ref_name = ruleset.get("conditions", {}).get("ref_name", {})
    includes = ref_name.get("include", [])
    excludes = ref_name.get("exclude", [])
    if not isinstance(includes, list) or not includes:
        return False

    branch_ref = f"refs/heads/{default_branch}"
    included = any(isinstance(pattern, str) and fnmatch(branch_ref, pattern) for pattern in includes)
    excluded = any(isinstance(pattern, str) and fnmatch(branch_ref, pattern) for pattern in excludes)
    return included and not excluded


def normalize_ruleset_rules(ruleset: dict | None) -> dict[str, dict]:
    return rules_by_type(extract_rules(ruleset))


def rule_is_covered(rule: dict, covering_rules: dict[str, dict]) -> bool:
    rule_type = rule.get("type")
    if not isinstance(rule_type, str):
        return False

    covering_rule = covering_rules.get(rule_type)
    if not covering_rule:
        return False

    if rule_type != "pull_request":
        return True

    parameters = rule.get("parameters")
    covering_parameters = covering_rule.get("parameters")
    if not isinstance(parameters, dict) or not isinstance(covering_parameters, dict):
        return False
    return parameters == covering_parameters


def candidate_legacy_rulesets(metadata: RepoMetadata, rulesets: list[dict]) -> list[dict]:
    return [
        item
        for item in rulesets
        if ref_includes_default_branch(item, metadata.default_branch) and item.get("name") != BASELINE_RULESET_NAME
    ]


def summarize_legacy_rulesets(metadata: RepoMetadata, rulesets: list[dict]) -> dict:
    baseline_ruleset = find_ruleset_by_name(rulesets)
    active_default_branch_rulesets = [
        item for item in rulesets if ref_includes_default_branch(item, metadata.default_branch)
    ]
    baseline_rule_map = normalize_ruleset_rules(baseline_ruleset)

    candidates = []
    for item in candidate_legacy_rulesets(metadata, rulesets):
        candidate_rules = extract_rules(item)
        remaining_rule_maps = [
            normalize_ruleset_rules(other)
            for other in active_default_branch_rulesets
            if other is not item
        ]
        coverage_reasons: list[str] = []
        uncovered_rule_types: list[str] = []

        for rule in candidate_rules:
            if rule_is_covered(rule, baseline_rule_map):
                continue
            if any(rule_is_covered(rule, other_map) for other_map in remaining_rule_maps):
                continue

            rule_type = rule.get("type")
            if isinstance(rule_type, str):
                uncovered_rule_types.append(rule_type)
                coverage_reasons.append(f"rule '{rule_type}' is not covered by remaining active rulesets")
            else:
                coverage_reasons.append("encountered a rule without a valid type")

        candidates.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "rule_types": sorted(normalize_ruleset_rules(item).keys()),
                "deletable": not uncovered_rule_types,
                "uncovered_rule_types": sorted(set(uncovered_rule_types)),
                "manual_action_required": bool(uncovered_rule_types),
                "coverage_reasons": coverage_reasons,
                "covered_by_baseline_only": all(rule_is_covered(rule, baseline_rule_map) for rule in candidate_rules),
            }
        )

    return {
        "repo": metadata.name_with_owner,
        "default_branch": metadata.default_branch,
        "baseline_ruleset_name": BASELINE_RULESET_NAME,
        "legacy_rulesets": candidates,
    }


def summarize_classic_branch_protection(metadata: RepoMetadata, protection: dict | None, effective_rules: list[dict]) -> dict:
    if not protection:
        return {
            "repo": metadata.name_with_owner,
            "default_branch": metadata.default_branch,
            "classic_branch_protection_found": False,
            "deletable": False,
            "manual_action_required": False,
            "coverage_reasons": [],
            "uncovered_settings": [],
            "covered_settings": [],
        }

    required_pull_request_reviews = protection.get("required_pull_request_reviews")
    allow_force_pushes = protection.get("allow_force_pushes", {}).get("enabled")
    allow_deletions = protection.get("allow_deletions", {}).get("enabled")

    effective_rule_map = rules_by_type(effective_rules)
    covered_settings: list[str] = []
    uncovered_settings: list[str] = []
    coverage_reasons: list[str] = []

    if required_pull_request_reviews is not None and pull_request_parameters_match(effective_rule_map.get("pull_request")):
        covered_settings.append("required_pull_request_reviews")
    elif required_pull_request_reviews is not None:
        uncovered_settings.append("required_pull_request_reviews")
        coverage_reasons.append("classic required_pull_request_reviews is not covered by effective pull_request rule")

    if allow_force_pushes is False and "non_fast_forward" in effective_rule_map:
        covered_settings.append("allow_force_pushes=false")
    elif allow_force_pushes is False:
        uncovered_settings.append("allow_force_pushes=false")
        coverage_reasons.append("classic force-push restriction is not covered by effective non_fast_forward rule")

    if allow_deletions is False and "deletion" in effective_rule_map:
        covered_settings.append("allow_deletions=false")
    elif allow_deletions is False:
        uncovered_settings.append("allow_deletions=false")
        coverage_reasons.append("classic deletion restriction is not covered by effective deletion rule")

    extra_settings = []
    if protection.get("required_status_checks") is not None:
        extra_settings.append("required_status_checks")
    if protection.get("enforce_admins", {}).get("enabled") is True:
        extra_settings.append("enforce_admins")
    if protection.get("restrictions") is not None:
        extra_settings.append("restrictions")
    if protection.get("required_linear_history", {}).get("enabled") is True:
        extra_settings.append("required_linear_history")
    if protection.get("required_conversation_resolution", {}).get("enabled") is True:
        extra_settings.append("required_conversation_resolution")
    if protection.get("block_creations", {}).get("enabled") is True:
        extra_settings.append("block_creations")
    if protection.get("lock_branch", {}).get("enabled") is True:
        extra_settings.append("lock_branch")
    if protection.get("allow_fork_syncing", {}).get("enabled") is True:
        extra_settings.append("allow_fork_syncing")

    if extra_settings:
        uncovered_settings.extend(extra_settings)
        coverage_reasons.extend(
            f"classic setting '{setting}' is outside the managed baseline and requires manual review"
            for setting in extra_settings
        )

    return {
        "repo": metadata.name_with_owner,
        "default_branch": metadata.default_branch,
        "classic_branch_protection_found": True,
        "deletable": not uncovered_settings,
        "manual_action_required": bool(uncovered_settings),
        "coverage_reasons": coverage_reasons,
        "uncovered_settings": uncovered_settings,
        "covered_settings": covered_settings,
    }


def find_ruleset_by_identifier(rulesets: list[dict], identifier: str) -> dict | None:
    for item in rulesets:
        if str(item.get("id")) == identifier or item.get("name") == identifier:
            return item
    return None


def summarize_ruleset_status(metadata: RepoMetadata, effective_rules: list[dict], rulesets: list[dict]) -> dict:
    effective_rule_map = rules_by_type(effective_rules)
    managed_ruleset = find_ruleset_by_name(rulesets)
    managed_rules = extract_rules(managed_ruleset)

    missing_rule_types = sorted(set(BASELINE_RULE_TYPES) - set(effective_rule_types(effective_rules)))
    extra_effective_rule_types = sorted(set(effective_rule_types(effective_rules)) - set(BASELINE_RULE_TYPES))

    return {
        "repo": metadata.name_with_owner,
        "visibility": metadata.visibility,
        "default_branch": metadata.default_branch,
        "baseline_ruleset_name": BASELINE_RULESET_NAME,
        "managed_ruleset_id": managed_ruleset.get("id") if managed_ruleset else None,
        "managed_ruleset_found": managed_ruleset is not None,
        "effective_rule_types": effective_rule_types(effective_rules),
        "missing_rule_types": missing_rule_types,
        "extra_effective_rule_types": extra_effective_rule_types,
        "pull_request_parameters_match_baseline": pull_request_parameters_match(
            effective_rule_map.get("pull_request")
        ),
        "managed_pull_request_parameters_match_baseline": pull_request_parameters_match(
            rules_by_type(managed_rules).get("pull_request")
        ),
        "baseline_rule_types_present": not missing_rule_types,
        "baseline_compliant": not missing_rule_types
        and pull_request_parameters_match(effective_rule_map.get("pull_request")),
    }
