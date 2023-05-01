import hashlib
from pathlib import Path
from unittest import mock

import pytest
from github3.git import Tree
from github3.repos import Repository

from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.util import CommitDir
from cumulusci.utils import temporary_dir


@pytest.fixture
def repo():
    repo = mock.Mock(spec=Repository)
    repo.owner = "SalesforceFoundation"
    repo.name = "TestRepo"
    return repo


class TestCommitDir:
    def test_call(self, repo, tmp_path):
        repo.git_commit.tree.sha = mock.Mock()
        repo.create_blob.return_value = "mocked_sha_hash"
        repo.tree = mock.Mock()
        repo.tree.return_value = Tree(
            {
                "url": "string",
                "sha": "tree-ish-hash",
                "tree": [
                    {
                        "type": "tree",
                        "mode": "100644",
                        "path": "dir",
                        "sha": "bogus1",
                    },
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": "file_outside_dir",
                        "sha": "bogus2",
                    },
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": "dir/deleteme",
                        "sha": "deletedfilesha",
                    },
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": "dir/unchanged",
                        "sha": hashlib.sha1(b"blob 0\0").hexdigest(),
                    },
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": "dir/modified",
                        "sha": "bogus3",
                    },
                    {
                        "type": "blob",
                        "mode": "100644",
                        "path": "dir/modified_bin",
                        "sha": "bogus4",
                    },
                ],
            },
            None,
        )

        commit = CommitDir(repo)
        Path(tmp_path, "unchanged").write_text("")
        Path(tmp_path, "modified").write_text("modified")
        Path(tmp_path, "new").write_text("new")
        Path(tmp_path, ".hidden").write_text(".hidden")
        Path(tmp_path, "modified_bin").write_bytes(b"\x9c")
        Path(tmp_path, "new_bin").write_bytes(b"\x9c")

        commit(tmp_path, "main", "dir", dry_run=True)
        expected_tree = [
            {"type": "blob", "mode": "100644", "path": "dir/deleteme", "sha": None},
            {
                "type": "blob",
                "mode": "100644",
                "path": "dir/modified",
                "content": "modified",
            },
            {
                "type": "blob",
                "mode": "100644",
                "path": "dir/modified_bin",
                "sha": "mocked_sha_hash",
            },
            {"path": "dir/new", "mode": "100644", "type": "blob", "content": "new"},
            {
                "path": "dir/new_bin",
                "mode": "100644",
                "type": "blob",
                "sha": "mocked_sha_hash",
            },
        ]
        commit(tmp_path, "main", "dir", commit_message="msg")
        assert len(commit.new_tree_list) == len(expected_tree)
        assert all(item in commit.new_tree_list for item in expected_tree)
        repo.create_tree.assert_called_once()
        assert commit.new_tree_list == repo.create_tree.call_args.args[0]
        assert "base_tree" in repo.create_tree.call_args.kwargs
        repo.create_commit.assert_called_once()

    def test_call__no_changes(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            repo.tree = mock.Mock(
                return_value=Tree(
                    {"url": "string", "sha": "tree-ish-hash", "tree": []}, None
                )
            )
            commit = CommitDir(repo)
            commit(d, "main", commit_message="msg")
        repo.create_commit.assert_not_called()

    def test_validate_dirs(self):
        repo = mock.Mock(spec=Repository)
        commit = CommitDir(repo)
        with pytest.raises(GithubException):
            commit._validate_dirs("bogus", None)
        _, repo_dir = commit._validate_dirs(".", None)
        assert repo_dir == ""
        _, repo_dir = commit._validate_dirs(".", "./test/")
        assert repo_dir == "test"

    def test_call__error_creating_tree(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            repo.create_tree.return_value = None
            repo.tree = mock.Mock(
                return_value=Tree(
                    {"url": "string", "sha": "tree-ish-hash", "tree": []}, None
                )
            )
            with open("new", "w") as f:
                f.write("new")
            commit = CommitDir(repo)
            with pytest.raises(GithubException):
                commit(d, "main", commit_message="msg")

    def test_call__error_creating_commit(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            repo.create_commit.return_value = None
            repo.tree = mock.Mock(
                return_value=Tree(
                    {"url": "string", "sha": "tree-ish-hash", "tree": []}, None
                )
            )
            with open("new", "w") as f:
                f.write("new")
            commit = CommitDir(repo)
            with pytest.raises(GithubException):
                commit(d, "main", commit_message="msg")

    def test_call__error_updating_head(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            head = mock.Mock()
            head.update.return_value = None
            repo.ref.return_value = head
            repo.tree = mock.Mock(
                return_value=Tree(
                    {"url": "string", "sha": "tree-ish-hash", "tree": []}, None
                )
            )
            with open("new", "w") as f:
                f.write("new")
            commit = CommitDir(repo)
            with pytest.raises(GithubException):
                commit(d, "main", commit_message="msg")

    def test_content_or_sha__dry_run(self, repo):
        commit = CommitDir(repo)
        result = commit._get_content_or_sha(b"content goes here", True)
        assert result == {"content": None}

    def test_content_or_sha__text_content(self, repo):
        commit = CommitDir(repo)
        result = commit._get_content_or_sha(b"content goes here", False)
        assert result == {"content": "content goes here"}

    def test_content_or_sha__binary_sha(self, repo):
        commit = CommitDir(repo)
        repo.create_blob.return_value = "binary-sha"
        result = commit._get_content_or_sha(b"\x9c", False)
        repo.create_blob.assert_called_once_with("nA==", "base64")
        assert result == {"sha": "binary-sha"}

    def test_create_blob__error(self, repo):
        commit = CommitDir(repo)
        repo.create_blob.return_value = None
        with pytest.raises(GithubException):
            commit._get_content_or_sha(b"\x9c", False)
