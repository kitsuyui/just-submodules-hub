from just_submodules_hub.repo_paths import normalize_repo_input, repo_display_name, repo_owner


def test_normalize_repo_input_accepts_slug() -> None:
    assert normalize_repo_input("kitsuyui/example") == "repo/github.com/kitsuyui/example"


def test_normalize_repo_input_accepts_https_url() -> None:
    assert normalize_repo_input("https://github.com/kitsuyui/example.git") == "repo/github.com/kitsuyui/example"


def test_normalize_repo_input_accepts_ssh_url() -> None:
    assert normalize_repo_input("git@github.com:kitsuyui/example.git") == "repo/github.com/kitsuyui/example"


def test_repo_helpers_strip_prefix() -> None:
    repo_path = "repo/github.com/kitsuyui/example"
    assert repo_display_name(repo_path) == "kitsuyui/example"
    assert repo_owner(repo_path) == "kitsuyui"


def test_normalize_repo_input_rejects_missing_repo_name() -> None:
    try:
        normalize_repo_input("kitsuyui")
    except ValueError as exc:
        assert "owner and repo" in str(exc)
    else:
        raise AssertionError("normalize_repo_input should reject invalid input")


def test_repo_helpers_accept_plain_slug() -> None:
    assert repo_display_name("kitsuyui/example") == "kitsuyui/example"
    assert repo_owner("kitsuyui/example") == "kitsuyui"
