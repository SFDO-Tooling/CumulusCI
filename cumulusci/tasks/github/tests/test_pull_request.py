from unittest import mock
import unittest

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.tasks.github import PullRequests
from cumulusci.tests.util import create_project_config


class TestPullRequests(unittest.TestCase):
    def test_run_task(self):
        project_config = create_project_config()
        project_config.keychain.set_service(
            "github",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "password": "TestPass",
                    "email": "testuser@testdomain.com",
                }
            ),
        )
        task_config = TaskConfig()
        task = PullRequests(project_config, task_config)
        repo = mock.Mock()
        repo.pull_requests.return_value = [mock.Mock(number=1, title="Test PR")]
        task.get_repo = mock.Mock(return_value=repo)
        task.logger = mock.Mock()
        task()
        task.logger.info.assert_called_with("#1: Test PR")
