import mock
import pytest
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.tests.util import create_project_config
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.release_notes.task import GithubReleaseNotes
from cumulusci.tasks.release_notes.task import ParentPullRequestNotes


class TestGithubReleaseNotes:
    @mock.patch("cumulusci.tasks.release_notes.task.GithubReleaseNotesGenerator")
    def test_run_GithubReleaseNotes_task(self, GithubReleaseNotesGenerator):
        generator = mock.Mock(return_value="notes")
        GithubReleaseNotesGenerator.return_value = generator
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
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = GithubReleaseNotes(project_config, task_config)
        task.github = mock.Mock()
        task.get_repo = mock.Mock()
        task()
        generator.assert_called_once()


class TestParentPullRequestNotes:
    @mock.patch("cumulusci.tasks.release_notes.task.ParentPullRequestNotes")

    def _get_ParentPullRequestNotes_generator(self, task_config)
    def test_run_task(self, ParentPullRequestNotes):
        generator = mock.Mock(return_value=None)
        ParentPullRequestNotes.return_value = generator
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
        task_config = TaskConfig({"options": {"branch_name": "test_branch"}})
        task = ParentPullRequestNotes(project_config, task_config)
        task.github = mock.Mock()
        task.get_repo = mock.Mock()
        task()
        generator.assert_called_once()

    def test_run_task_without_options(self):
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
        task_config = TaskConfig({"options": {}})
        task = ParentPullRequestNotes(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task()
