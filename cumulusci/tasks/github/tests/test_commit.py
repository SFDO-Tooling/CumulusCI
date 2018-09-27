import mock
import os
import unittest

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import GithubException
from cumulusci.tasks.github import CommitApexDocs
from cumulusci.tests.util import create_project_config


@mock.patch("cumulusci.tasks.github.base.get_github_api", mock.Mock())
class TestCommitApexDocs(unittest.TestCase):
    def setUp(self):
        self.project_config = create_project_config()
        self.project_config.config["project"]["apexdoc"] = {
            "branch": "master",
            "dir": "docs",
            "repo_dir": "docs",
        }
        self.project_config.keychain.set_service(
            "github",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "password": "TestPass",
                    "email": "testuser@testdomain.com",
                }
            ),
        )

    @mock.patch("cumulusci.tasks.github.commit.CommitDir")
    def test_run_task(self, CommitDir):
        task_config = TaskConfig()
        task = CommitApexDocs(self.project_config, task_config)
        commit_dir = mock.Mock()
        CommitDir.return_value = commit_dir
        task()
        commit_dir.assert_called_once_with(
            os.path.join("docs", "ApexDocumentation"),
            "master",
            "docs",
            "Update Apex docs",
            False,
        )

    def test_run_task__missing_branch(self):
        del self.project_config.config["project"]["apexdoc"]
        task_config = TaskConfig()
        task = CommitApexDocs(self.project_config, task_config)
        with self.assertRaises(GithubException):
            task()
