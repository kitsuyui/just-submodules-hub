from pathlib import Path
from subprocess import CompletedProcess

import pytest

import just_submodules_hub.github_prs as github_prs
from just_submodules_hub.github_prs import (
    ActionRequiredPullRequestRecord,
    PullRequestRecord,
    PullRequestState,
    ReadyPullRequestRecord,
    action_required_reasons,
    build_pull_request_record,
    filter_managed_pull_requests,
    gh_pr_list_args,
    gh_search_args,
    has_failed_checks,
    has_only_green_checks,
    has_pending_checks,
    is_missing_repository_error,
    parse_action_required_pull_requests,
    parse_pull_request_payload,
    parse_ready_pull_requests,
    render_action_required_pull_requests_tsv,
    render_pull_requests_tsv,
    render_ready_pull_requests_tsv,
    validate_state,
)


def test_gh_pr_view_reports_timeout_as_unknown(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(github_prs.shutil, "which", lambda name: "/usr/bin/gh")
    monkeypatch.setattr(
        github_prs,
        "run_gh",
        lambda args, cwd: CompletedProcess(
            ["gh", *args],
            124,
            stdout="",
            stderr="gh command timed out after 60 seconds",
        ),
    )

    assert github_prs.gh_pr_view(tmp_path) == PullRequestState(
        "",
        "unknown",
        "",
        "gh command timed out after 60 seconds",
    )


def test_gh_search_args_for_merged() -> None:
    assert gh_search_args("kitsuyui", "merged")[-1] == "--merged"


def test_parse_and_filter_pull_requests() -> None:
    payload = """
[
  {
    "repository": {"nameWithOwner": "kitsuyui/ts-playground"},
    "author": {"login": "kitsuyui"},
    "url": "https://example.com/pr/1"
  },
  {
    "repository": {"nameWithOwner": "other/ignored"},
    "author": {"login": "someone"},
    "url": "https://example.com/pr/2"
  }
]
"""
    records = parse_pull_request_payload(payload)
    filtered = filter_managed_pull_requests(
        records,
        [
            "repo/github.com/kitsuyui/ts-playground",
            "repo/github.com/kitsuyui/react-playground",
        ],
    )
    assert filtered == [
        PullRequestRecord(
            repo="kitsuyui/ts-playground",
            author="kitsuyui",
            url="https://example.com/pr/1",
        ),
    ]


def test_render_pull_requests_tsv() -> None:
    output = render_pull_requests_tsv(
        [
            PullRequestRecord(
                repo="kitsuyui/ts-playground",
                author="kitsuyui",
                url="https://example.com/pr/1",
            ),
        ],
    )
    assert (
        output
        == "repo\tauthor\turl\nkitsuyui/ts-playground\tkitsuyui\thttps://example.com/pr/1\n"
    )


def test_build_pull_request_record_rejects_incomplete_payload() -> None:
    assert (
        build_pull_request_record(
            {"repository": {"nameWithOwner": "kitsuyui/ts-playground"}},
        )
        is None
    )


def test_validate_state_rejects_unknown_state() -> None:
    try:
        validate_state("draft")
    except ValueError as exc:
        assert str(exc) == "STATE must be one of: open, closed, merged, all"
    else:
        raise AssertionError("validate_state should reject unknown state")


def test_gh_pr_list_args_targets_the_repo() -> None:
    args = gh_pr_list_args("kitsuyui/ts-playground")
    assert args[:3] == ["gh", "pr", "list"]
    assert "kitsuyui/ts-playground" in args
    assert "mergeStateStatus" in args[-1]
    assert "statusCheckRollup" in args[-1]


def test_parse_ready_pull_requests_keeps_only_mergeable_green_prs() -> None:
    payload = """
[
  {
    "author": {"login": "app/renovate"},
    "isDraft": false,
    "mergeStateStatus": "CLEAN",
    "mergeable": "MERGEABLE",
    "url": "https://example.com/pr/1"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "UNSTABLE",
    "mergeable": "MERGEABLE",
    "statusCheckRollup": [
      {"name": "test", "conclusion": "SUCCESS"},
      {"context": "octocov", "state": "SUCCESS"}
    ],
    "url": "https://example.com/pr/2"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "UNSTABLE",
    "mergeable": "MERGEABLE",
    "statusCheckRollup": [
      {"name": "test", "conclusion": "SUCCESS"},
      {"name": "deploy", "conclusion": "FAILURE"}
    ],
    "url": "https://example.com/pr/6"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "UNSTABLE",
    "mergeable": "MERGEABLE",
    "statusCheckRollup": [
      {"name": "test", "status": "IN_PROGRESS", "conclusion": ""}
    ],
    "url": "https://example.com/pr/7"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": true,
    "mergeStateStatus": "CLEAN",
    "mergeable": "MERGEABLE",
    "url": "https://example.com/pr/3"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "DIRTY",
    "mergeable": "CONFLICTING",
    "url": "https://example.com/pr/4"
  },
  {
    "author": {"login": "kitsuyui"},
    "isDraft": false,
    "mergeStateStatus": "BLOCKED",
    "mergeable": "MERGEABLE",
    "url": "https://example.com/pr/5"
  }
]
"""
    records = parse_ready_pull_requests(payload, "kitsuyui/ts-playground")
    assert [record.url for record in records] == [
        "https://example.com/pr/1",
        "https://example.com/pr/2",
    ]


def test_has_only_green_checks_accepts_green_and_empty_rollups() -> None:
    assert has_only_green_checks(None)
    assert has_only_green_checks([])
    assert has_only_green_checks(
        [
            {"name": "test", "conclusion": "SUCCESS"},
            {"name": "lint", "conclusion": "NEUTRAL"},
            {"name": "optional", "conclusion": "SKIPPED"},
            {"context": "octocov", "state": "SUCCESS"},
        ],
    )


def test_has_only_green_checks_rejects_failing_pending_and_cancelled() -> None:
    assert not has_only_green_checks([{"name": "test", "conclusion": "FAILURE"}])
    assert not has_only_green_checks([{"context": "ci", "state": "ERROR"}])
    assert not has_only_green_checks([{"name": "test", "conclusion": "CANCELLED"}])
    # A CheckRun that has not completed yet has an empty conclusion.
    assert not has_only_green_checks(
        [{"name": "test", "status": "IN_PROGRESS", "conclusion": ""}],
    )
    assert not has_only_green_checks([{"context": "ci", "state": "PENDING"}])


def test_check_state_helpers_distinguish_failed_pending_and_green() -> None:
    assert has_failed_checks([{"name": "test", "conclusion": "FAILURE"}])
    assert not has_failed_checks([{"name": "test", "conclusion": ""}])
    assert has_pending_checks([{"name": "test", "conclusion": ""}])
    assert has_pending_checks([{"context": "ci", "state": "PENDING"}])
    assert not has_pending_checks([{"name": "test", "conclusion": "SUCCESS"}])


def test_action_required_reasons_classifies_stable_blockers() -> None:
    cases: list[tuple[dict[str, object], tuple[str, ...]]] = [
        ({"isDraft": True}, ("draft",)),
        (
            {"mergeable": "CONFLICTING", "mergeStateStatus": "DIRTY"},
            ("merge_conflict",),
        ),
        (
            {"reviewDecision": "CHANGES_REQUESTED"},
            ("changes_requested",),
        ),
        ({"reviewDecision": "REVIEW_REQUIRED"}, ("review_required",)),
        (
            {"statusCheckRollup": [{"conclusion": "FAILURE"}]},
            ("checks_failed",),
        ),
        ({"mergeStateStatus": "BEHIND"}, ("branch_behind",)),
        ({"mergeStateStatus": "BLOCKED"}, ("repository_policy",)),
    ]
    for item, reasons in cases:
        assert action_required_reasons(item) == reasons


def test_action_required_reasons_excludes_states_that_can_settle() -> None:
    assert action_required_reasons({"mergeable": "UNKNOWN"}) == ()
    assert (
        action_required_reasons(
            {
                "mergeStateStatus": "BLOCKED",
                "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}],
            },
        )
        == ()
    )


def test_parse_and_render_action_required_pull_requests() -> None:
    payload = """
[
  {
    "author": {"login": "kitsuyui"},
    "isDraft": true,
    "mergeStateStatus": "DIRTY",
    "mergeable": "CONFLICTING",
    "url": "https://example.com/pr/1"
  },
  {
    "author": {"login": "app/renovate"},
    "mergeStateStatus": "UNSTABLE",
    "mergeable": "MERGEABLE",
    "statusCheckRollup": [{"status": "IN_PROGRESS", "conclusion": ""}],
    "url": "https://example.com/pr/2"
  }
]
"""
    records = parse_action_required_pull_requests(
        payload,
        "kitsuyui/ts-playground",
    )
    assert records == [
        ActionRequiredPullRequestRecord(
            repo="kitsuyui/ts-playground",
            author="kitsuyui",
            reasons=("draft", "merge_conflict"),
            url="https://example.com/pr/1",
        ),
    ]
    assert render_action_required_pull_requests_tsv(records) == (
        "repo\tauthor\treasons\turl\n"
        "kitsuyui/ts-playground\tkitsuyui\tdraft,merge_conflict\t"
        "https://example.com/pr/1\n"
    )
    assert records[0].operator_required


def test_action_required_record_distinguishes_automatable_repair() -> None:
    record = ActionRequiredPullRequestRecord(
        repo="kitsuyui/ts-playground",
        author="kitsuyui",
        reasons=("merge_conflict", "checks_failed"),
        url="https://example.com/pr/2",
    )
    assert not record.operator_required


def test_render_ready_pull_requests_tsv_sorts_and_dedupes() -> None:
    record = ReadyPullRequestRecord(
        repo="kitsuyui/ts-playground",
        author="kitsuyui",
        merge_state="CLEAN",
        url="https://example.com/pr/1",
    )
    output = render_ready_pull_requests_tsv([record, record])
    assert output == (
        "repo\tauthor\tmerge_state\turl\n"
        "kitsuyui/ts-playground\tkitsuyui\tCLEAN\thttps://example.com/pr/1\n"
    )


def test_is_missing_repository_error_matches_gh_graphql_message() -> None:
    assert is_missing_repository_error(
        "GraphQL: Could not resolve to a Repository with the name "
        "'kitsuyui/example.wiki'. (repository)",
    )
    assert not is_missing_repository_error("gh: rate limit exceeded")
