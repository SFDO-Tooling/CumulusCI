import mock
import os
import unittest

from github3.repos import Repository
from cumulusci.tasks.github.util import CommitDir
from cumulusci.utils import temporary_dir


class TestCommitDir(unittest.TestCase):
    def test_call(self):
        with temporary_dir() as d:
            repo = mock.Mock(spec=Repository)
            repo.tree = mock.Mock(
                return_value=mock.Mock(
                    recurse=mock.Mock(
                        return_value=mock.Mock(
                            to_json=mock.Mock(
                                return_value={
                                    "tree": [
                                        {
                                            "type": "blob",
                                            "path": os.path.join(d, "file"),
                                            "sha": "bogus",
                                        }
                                    ]
                                }
                            )
                        )
                    )
                )
            )
            commit = CommitDir(repo)
            with open(os.path.join(d, "file"), "w") as f:
                f.write("new")
            commit(d, "master", commit_message="msg")
        repo.create_commit.assert_called_once()
