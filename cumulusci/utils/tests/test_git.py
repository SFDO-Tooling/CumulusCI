import pytest

from cumulusci.utils.git import (
    EMPTY_URL_MESSAGE,
    construct_release_branch_name,
    get_release_identifier,
    is_release_branch,
    is_release_branch_or_child,
    parse_repo_url,
    split_repo_url,
)


def test_is_release_branch():
    assert is_release_branch("feature/230", "feature/")
    assert not is_release_branch("feature/230__test", "feature/")
    assert not is_release_branch("main", "feature/")


def test_is_release_branch_or_child():
    assert is_release_branch_or_child("feature/230", "feature/")
    assert is_release_branch_or_child("feature/230__test", "feature/")
    assert is_release_branch_or_child("feature/230__test__gc", "feature/")
    assert not is_release_branch_or_child("main", "feature/")


def test_get_release_identifier():
    assert get_release_identifier("feature/230", "feature/") == "230"
    assert get_release_identifier("feature/230__test", "feature/") == "230"
    assert get_release_identifier("main", "feature/") is None


def test_construct_release_branch_name():
    assert construct_release_branch_name("feature/", "230") == "feature/230"


@pytest.mark.parametrize(
    "repo_uri,owner,repo_name,host",
    [
        (
            "https://git.ent.example.com/org/private_repo/",
            "org",
            "private_repo",
            "git.ent.example.com",
        ),
        ("https://github.com/owner/repo_name/", "owner", "repo_name", "github.com"),
        ("https://github.com/owner/repo_name.git", "owner", "repo_name", "github.com"),
        (
            "https://user@github.com/owner/repo_name.git",
            "owner",
            "repo_name",
            "github.com",
        ),
        (
            "https://git.ent.example.com/org/private_repo.git",
            "org",
            "private_repo",
            "git.ent.example.com",
        ),
        ("git@github.com:owner/repo_name.git", "owner", "repo_name", "github.com"),
        ("git@github.com:/owner/repo_name.git", "owner", "repo_name", "github.com"),
        ("git@github.com:owner/repo_name", "owner", "repo_name", "github.com"),
        (
            "git@api.github.com/owner/repo_name/",
            "owner",
            "repo_name",
            "api.github.com",
        ),
        (
            "git@api.github.com/owner/repo_name.git",
            "owner",
            "repo_name",
            "api.github.com",
        ),
    ],
)
def test_parse_repo_url(repo_uri, owner, repo_name, host):
    assert parse_repo_url(repo_uri) == (owner, repo_name, host)
    assert split_repo_url(repo_uri) == (owner, repo_name)


@pytest.mark.parametrize("URL", [None, ""])
def test_empty_url(URL):
    with pytest.raises(ValueError, match=EMPTY_URL_MESSAGE):
        parse_repo_url(URL)
