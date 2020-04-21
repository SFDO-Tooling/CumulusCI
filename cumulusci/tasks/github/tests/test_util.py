import hashlib
from unittest import mock
import unittest

from github3.repos import Repository
from github3.git import Tree
from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github.util import CommitDir
from cumulusci.utils import temporary_dir


class TestCommitDir(unittest.TestCase):
    def test_call(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            repo.owner = "SalesforceFoundation"
            repo.name = "TestRepo"
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
                            "path": "dir/unchanged",
                            "sha": hashlib.sha1(b"blob 0\0").hexdigest(),
                        },
                        {
                            "type": "blob",
                            "mode": "100644",
                            "path": "dir/modified",
                            "sha": "bogus3",
                        },
                    ],
                },
                None,
            )

            commit = CommitDir(repo)
            with open("unchanged", "w") as f:
                f.write("")
            with open("modified", "w") as f:
                f.write("modified")
            with open("new", "w") as f:
                f.write("new")
            with open(".hidden", "w") as f:
                pass
            commit(d, "master", "dir", dry_run=True)
            assert commit.new_tree_list == [
                {
                    "sha": "bogus2",
                    "mode": "100644",
                    "path": "file_outside_dir",
                    "size": None,
                    "type": "blob",
                },
                {
                    "sha": hashlib.sha1(b"blob 0\0").hexdigest(),
                    "mode": "100644",
                    "path": "dir/unchanged",
                    "size": None,
                    "type": "blob",
                },
                {
                    "sha": None,
                    "mode": "100644",
                    "path": "dir/modified",
                    "size": None,
                    "type": "blob",
                },
                {"path": "dir/new", "mode": "100644", "type": "blob", "sha": None},
            ]
            commit(d, "master", "dir", commit_message="msg")
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
            commit(d, "master", commit_message="msg")
        repo.create_commit.assert_not_called()

    def test_validate_dirs(self):
        repo = mock.Mock(spec=Repository)
        commit = CommitDir(repo)
        with self.assertRaises(GithubException):
            commit._validate_dirs("bogus", None)
        _, repo_dir = commit._validate_dirs(".", None)
        self.assertEqual("", repo_dir)
        _, repo_dir = commit._validate_dirs(".", "./test/")
        self.assertEqual("test", repo_dir)

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
            with self.assertRaises(GithubException):
                commit(d, "master", commit_message="msg")

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
            with self.assertRaises(GithubException):
                commit(d, "master", commit_message="msg")

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
            with self.assertRaises(GithubException):
                commit(d, "master", commit_message="msg")

    def test_create_blob__handles_decode_error(self):
        repo = mock.Mock(spec=Repository)
        commit = CommitDir(repo)
        commit.dry_run = False
        self.assertTrue(commit._create_blob(b"\x9c", "local_path"))

    def test_create_blob__error(self):
        repo = mock.Mock(spec=Repository)
        repo.create_blob.return_value = None
        commit = CommitDir(repo)
        commit.dry_run = False
        with self.assertRaises(GithubException):
            self.assertTrue(commit._create_blob(b"", "local_path"))
