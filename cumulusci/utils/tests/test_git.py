from cumulusci.utils.git import (
    construct_release_branch_name,
    get_release_identifier,
    is_release_branch,
    is_release_branch_or_child,
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


def test_split_repo_url():
    assert split_repo_url("https://github.com/owner/repo") == ("owner", "repo")
    assert split_repo_url("https://github.com/owner/repo.git") == ("owner", "repo")
    assert split_repo_url("git@github.com:owner/repo") == ("owner", "repo")
    assert split_repo_url("git@alias:owner/repo") == ("owner", "repo")
