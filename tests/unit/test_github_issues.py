from just_submodules_hub.github_issues import (
    IssueRecord,
    build_issue_record,
    filter_managed_issues,
    gh_search_args,
    parse_issue_payload,
    render_issues_tsv,
    validate_state,
)


def test_gh_search_args_for_all_has_no_state_filter() -> None:
    assert "--state" not in gh_search_args("kitsuyui", "all")


def test_gh_search_args_for_open_has_state_filter() -> None:
    assert gh_search_args("kitsuyui", "open")[-2:] == ["--state", "open"]


def test_parse_and_filter_issues() -> None:
    payload = """
[
  {
    "repository": {"nameWithOwner": "kitsuyui/ts-playground"},
    "author": {"login": "kitsuyui"},
    "url": "https://example.com/issues/1"
  },
  {
    "repository": {"nameWithOwner": "other/ignored"},
    "author": {"login": "someone"},
    "url": "https://example.com/issues/2"
  }
]
"""
    records = parse_issue_payload(payload)
    filtered = filter_managed_issues(
        records,
        [
            "repo/github.com/kitsuyui/ts-playground",
            "repo/github.com/kitsuyui/react-playground",
        ],
    )
    assert filtered == [
        IssueRecord(
            repo="kitsuyui/ts-playground",
            author="kitsuyui",
            url="https://example.com/issues/1",
        )
    ]


def test_render_issues_tsv() -> None:
    output = render_issues_tsv(
        [
            IssueRecord(
                repo="kitsuyui/ts-playground",
                author="kitsuyui",
                url="https://example.com/issues/1",
            )
        ]
    )
    assert (
        output
        == "repo\tauthor\turl\nkitsuyui/ts-playground\tkitsuyui\thttps://example.com/issues/1\n"
    )


def test_build_issue_record_rejects_incomplete_payload() -> None:
    assert (
        build_issue_record({"repository": {"nameWithOwner": "kitsuyui/ts-playground"}})
        is None
    )


def test_validate_state_rejects_unknown_state() -> None:
    try:
        validate_state("merged")
    except ValueError as exc:
        assert str(exc) == "STATE must be one of: open, closed, all"
    else:
        raise AssertionError("validate_state should reject unknown state")
