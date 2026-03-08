import json

from just_submodules_hub.github_rulesets import (
    BASELINE_PULL_REQUEST_PARAMETERS,
    BASELINE_RULESET_NAME,
    RepoMetadata,
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


def test_parse_repo_metadata_extracts_default_branch_and_visibility() -> None:
    payload = """
{
  "nameWithOwner": "kitsuyui/example",
  "visibility": "PUBLIC",
  "defaultBranchRef": {"name": "main"}
}
"""
    metadata = parse_repo_metadata(payload)
    assert metadata == RepoMetadata(
        name_with_owner="kitsuyui/example",
        visibility="public",
        default_branch="main",
    )


def test_desired_ruleset_payload_targets_default_branch() -> None:
    payload = desired_ruleset_payload("main")
    assert payload["name"] == BASELINE_RULESET_NAME
    assert payload["conditions"]["ref_name"]["include"] == ["refs/heads/main"]
    assert payload["rules"][0]["parameters"] == BASELINE_PULL_REQUEST_PARAMETERS


def test_find_ruleset_by_name_returns_matching_ruleset() -> None:
    rulesets = [{"id": 1, "name": "other"}, {"id": 2, "name": BASELINE_RULESET_NAME}]
    assert find_ruleset_by_name(rulesets) == {"id": 2, "name": BASELINE_RULESET_NAME}


def test_summarize_ruleset_status_marks_baseline_compliant() -> None:
    metadata = RepoMetadata("kitsuyui/example", "public", "main")
    effective_rules = parse_json_payload(
        json.dumps(
            [
                {"type": "pull_request", "parameters": BASELINE_PULL_REQUEST_PARAMETERS},
                {"type": "non_fast_forward"},
                {"type": "deletion"},
            ]
        )
    )
    rulesets = parse_json_payload(
        json.dumps([{"id": 7, "name": BASELINE_RULESET_NAME, "rules": effective_rules}])
    )

    summary = summarize_ruleset_status(metadata, effective_rules, rulesets)

    assert summary["baseline_compliant"] is True
    assert summary["managed_ruleset_found"] is True
    assert summary["managed_ruleset_id"] == 7
    assert summary["missing_rule_types"] == []
    assert summary["managed_pull_request_parameters_match_baseline"] is True


def test_summarize_ruleset_status_reports_parameter_drift() -> None:
    metadata = RepoMetadata("kitsuyui/example", "private", "main")
    effective_rules = parse_json_payload(
        json.dumps(
            [
                {
                    "type": "pull_request",
                    "parameters": {
                        **BASELINE_PULL_REQUEST_PARAMETERS,
                        "required_review_thread_resolution": True,
                    },
                },
                {"type": "non_fast_forward"},
                {"type": "deletion"},
            ]
        )
    )

    summary = summarize_ruleset_status(metadata, effective_rules, [])

    assert summary["baseline_rule_types_present"] is True
    assert summary["pull_request_parameters_match_baseline"] is False
    assert summary["baseline_compliant"] is False


def test_summarize_legacy_rulesets_marks_extra_rule_as_manual_review() -> None:
    metadata = RepoMetadata("kitsuyui/example", "public", "main")
    rulesets = parse_json_payload(
        json.dumps(
            [
                {
                    "id": 7,
                    "name": BASELINE_RULESET_NAME,
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                    "rules": [
                        {"type": "pull_request", "parameters": BASELINE_PULL_REQUEST_PARAMETERS},
                        {"type": "non_fast_forward"},
                        {"type": "deletion"},
                    ],
                },
                {
                    "id": 9,
                    "name": "protect-main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                    "rules": [
                        {"type": "required_linear_history"},
                    ],
                },
            ]
        )
    )

    summary = summarize_legacy_rulesets(metadata, rulesets)
    legacy = summary["legacy_rulesets"][0]

    assert legacy["name"] == "protect-main"
    assert legacy["deletable"] is False
    assert legacy["uncovered_rule_types"] == ["required_linear_history"]


def test_candidate_legacy_rulesets_and_identifier_lookup() -> None:
    metadata = RepoMetadata("kitsuyui/example", "public", "main")
    rulesets = parse_json_payload(
        json.dumps(
            [
                {
                    "id": 7,
                    "name": BASELINE_RULESET_NAME,
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                    "rules": [{"type": "deletion"}],
                },
                {
                    "id": 11,
                    "name": "protect-main",
                    "target": "branch",
                    "enforcement": "active",
                    "conditions": {"ref_name": {"include": ["refs/heads/main"], "exclude": []}},
                    "rules": [{"type": "deletion"}],
                },
            ]
        )
    )

    legacy_rulesets = candidate_legacy_rulesets(metadata, rulesets)
    assert [item["name"] for item in legacy_rulesets] == ["protect-main"]
    assert find_ruleset_by_identifier(legacy_rulesets, "11") == legacy_rulesets[0]
    assert find_ruleset_by_identifier(legacy_rulesets, "protect-main") == legacy_rulesets[0]


def test_summarize_classic_branch_protection_marks_redundant_when_baseline_covers_it() -> None:
    metadata = RepoMetadata("kitsuyui/example", "public", "main")
    protection = {
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "required_status_checks": None,
        "restrictions": None,
        "enforce_admins": {"enabled": False},
        "required_linear_history": {"enabled": False},
        "required_conversation_resolution": {"enabled": False},
        "block_creations": {"enabled": False},
        "lock_branch": {"enabled": False},
        "allow_fork_syncing": {"enabled": False},
    }
    effective_rules = parse_json_payload(
        json.dumps(
            [
                {"type": "pull_request", "parameters": BASELINE_PULL_REQUEST_PARAMETERS},
                {"type": "non_fast_forward"},
                {"type": "deletion"},
            ]
        )
    )

    summary = summarize_classic_branch_protection(metadata, protection, effective_rules)

    assert summary["classic_branch_protection_found"] is True
    assert summary["deletable"] is True
    assert summary["uncovered_settings"] == []


def test_summarize_classic_branch_protection_requires_manual_review_for_extra_settings() -> None:
    metadata = RepoMetadata("kitsuyui/example", "public", "main")
    protection = {
        "required_pull_request_reviews": {"required_approving_review_count": 0},
        "allow_force_pushes": {"enabled": False},
        "allow_deletions": {"enabled": False},
        "required_status_checks": {"strict": True},
        "restrictions": None,
        "enforce_admins": {"enabled": False},
        "required_linear_history": {"enabled": False},
        "required_conversation_resolution": {"enabled": False},
        "block_creations": {"enabled": False},
        "lock_branch": {"enabled": False},
        "allow_fork_syncing": {"enabled": False},
    }
    effective_rules = parse_json_payload(
        json.dumps(
            [
                {"type": "pull_request", "parameters": BASELINE_PULL_REQUEST_PARAMETERS},
                {"type": "non_fast_forward"},
                {"type": "deletion"},
            ]
        )
    )

    summary = summarize_classic_branch_protection(metadata, protection, effective_rules)

    assert summary["deletable"] is False
    assert summary["uncovered_settings"] == ["required_status_checks"]
