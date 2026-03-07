from just_submodules_hub.github_prs import (
    PullRequestRecord,
    filter_managed_pull_requests,
    gh_search_args,
    parse_pull_request_payload,
    render_pull_requests_tsv,
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
        ["repo/github.com/kitsuyui/ts-playground", "repo/github.com/kitsuyui/react-playground"],
    )
    assert filtered == [
        PullRequestRecord(
            repo="kitsuyui/ts-playground",
            author="kitsuyui",
            url="https://example.com/pr/1",
        )
    ]


def test_render_pull_requests_tsv() -> None:
    output = render_pull_requests_tsv(
        [PullRequestRecord(repo="kitsuyui/ts-playground", author="kitsuyui", url="https://example.com/pr/1")]
    )
    assert output == "repo\tauthor\turl\nkitsuyui/ts-playground\tkitsuyui\thttps://example.com/pr/1\n"
