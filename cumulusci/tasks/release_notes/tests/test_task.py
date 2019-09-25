import mock
import pytest

from github3.pulls import ShortPullRequest

from cumulusci.core.config import TaskConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.tests.util import create_project_config
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.release_notes.task import GithubReleaseNotes
from cumulusci.tasks.release_notes.task import ParentPullRequestNotes
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin


class TestGithubReleaseNotes:
    @pytest.fixture
    def project_config(self):
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
        project_config.project__git__default_branch = "master"
        return project_config

    @mock.patch("cumulusci.tasks.release_notes.task.GithubReleaseNotesGenerator")
    def test_run_GithubReleaseNotes_task(
        self, GithubReleaseNotesGenerator, project_config
    ):
        generator = mock.Mock(return_value="notes")
        GithubReleaseNotesGenerator.return_value = generator
        task_config = TaskConfig({"options": {"tag": "release/1.0"}})
        task = GithubReleaseNotes(project_config, task_config)
        task.github = mock.Mock()
        task.get_repo = mock.Mock()
        task()
        generator.assert_called_once()


class TestParentPullRequestNotes(GithubApiTestMixin):

    BRANCH_NAME = "feature/long__test-branch"
    BUILD_NOTES_LABEL = "Build Notes"

    @pytest.fixture
    def project_config(self):
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
        return project_config

    @pytest.fixture
    def task_factory(self, project_config):
        def _task_factory(options):
            task_config = TaskConfig(options)
            task = ParentPullRequestNotes(project_config, task_config)
            task.repo = mock.Mock()
            task.repo.default_branch = "master"
            task.repo.owner.login = "SFDO-Tooling"
            task.logger = mock.Mock()
            task.github = mock.Mock()
            return task

        return _task_factory

    def test_run_task_without_options(self, task_factory):
        with pytest.raises(TaskOptionsError):
            task_factory({"options": {}})

    def test_run_task_with_both_options(self, task_factory):
        with pytest.raises(TaskOptionsError):
            task_factory(
                {
                    "options": {
                        "branch_name": "test_branch",
                        "parent_branch_name": "parent_branch",
                        "build_notes_label": self.BUILD_NOTES_LABEL,
                    }
                }
            )

    def test_run_task__branch_option(self, task_factory):
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task._handle_branch_name_option = mock.Mock()
        task._handle_parent_branch_name_option = mock.Mock()
        task._run_task()

        task._handle_branch_name_option.assert_called_once()
        assert (
            not task._handle_parent_branch_name_option.called
        ), "method should not have been called"

    def test_run_task__parent_branch_option(self, task_factory):
        task = task_factory(
            {
                "options": {
                    "parent_branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task._handle_branch_name_option = mock.Mock()
        task._handle_parent_branch_name_option = mock.Mock()
        task._run_task()

        task._handle_parent_branch_name_option.assert_called_once()
        assert (
            not task._handle_branch_name_option.called
        ), "method should not have been called"

    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_with_base_branch")
    def test_get_parent_pull_request__parent_pull_request_exists(
        self, get_pull_request, task_factory, project_config, gh_api
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this
        get_pull_request.return_value = [
            ShortPullRequest(self._get_expected_pull_request(1, 1, "Body"), gh_api)
        ]

        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task.repo.default_branch = "master"

        actual_pull_request = task._get_parent_pull_request(self.BRANCH_NAME)
        get_pull_request.assert_called_once_with(task.repo, "master", self.BRANCH_NAME)
        assert 1 == actual_pull_request.number
        assert "Body" == actual_pull_request.body

    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_with_base_branch")
    @mock.patch("cumulusci.tasks.release_notes.task.create_pull_request")
    @mock.patch("cumulusci.tasks.release_notes.task.add_labels_to_pull_request")
    def test_get_parent_pull_request__create_parent_pull_request(
        self,
        add_labels,
        create_pull_request,
        get_pull_request,
        task_factory,
        project_config,
        gh_api,
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this

        get_pull_request.return_value = []
        create_pull_request.return_value = ShortPullRequest(
            self._get_expected_pull_request(62, 62, "parent body"), gh_api
        )

        label_name = "Build Change Notes"
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": label_name,
                }
            }
        )
        task.build_notes_label = label_name

        actual_pull_request = task._get_parent_pull_request(self.BRANCH_NAME)
        get_pull_request.assert_called_once_with(
            task.repo, task.repo.default_branch, self.BRANCH_NAME
        )
        assert 62 == actual_pull_request.number
        assert "parent body" == actual_pull_request.body

    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_with_base_branch")
    def test_handle_parent_branch_name_option__no_branch_found(
        self, get_pull_request, task_factory, project_config
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this

        get_pull_request.return_value = []

        task = task_factory(
            {
                "options": {
                    "parent_branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )

        task._handle_parent_branch_name_option(mock.Mock(), self.BRANCH_NAME)
        task.logger.info.assert_called_once_with(
            "No pull request found for branch: {}. Exiting...".format(self.BRANCH_NAME)
        )

    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_with_base_branch")
    def test_handle_parent_branch_name_option__multiple_branches_found(
        self, get_pull_request, task_factory, project_config
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this

        get_pull_request.return_value = ["Pull Request 1", "Pull Request 2"]

        task = task_factory(
            {
                "options": {
                    "parent_branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )

        task._handle_parent_branch_name_option(mock.Mock(), self.BRANCH_NAME)
        task.logger.info.assert_called_once_with(
            "More than one pull request returned with base='master' for branch {}".format(
                self.BRANCH_NAME
            )
        )

    @mock.patch("cumulusci.tasks.release_notes.task.is_label_on_pull_request")
    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_with_base_branch")
    def test_handle_parent_branch_name_option__branch_found(
        self, get_pr, is_label_on_pr, task_factory, project_config, gh_api
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this

        pull_request = ShortPullRequest(
            self._get_expected_pull_request(1, 1, "Body"), gh_api
        )
        pull_request.base.ref = "master"
        get_pr.return_value = [pull_request]
        is_label_on_pr.return_value = True

        generator = mock.Mock()
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task._handle_parent_branch_name_option(generator, self.BRANCH_NAME)

        generator.aggregate_child_change_notes.assert_called_once_with(pull_request)

    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_by_head")
    def test_handle_branch_name_option__branch_not_child(self, get_pr, task_factory):
        get_pr.return_values = None
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task.logger = mock.Mock()

        generator = mock.Mock()
        get_pr.return_value = None

        not_child_branch = "not-child-branch-format"
        task._handle_branch_name_option(generator, not_child_branch)

        task.logger.info.assert_called_once_with(
            "Branch {} is not a child branch. Exiting...".format(not_child_branch)
        )

    @mock.patch("cumulusci.tasks.release_notes.task.is_label_on_pull_request")
    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_by_head")
    def test_handle_branch_name_option__review_label_found(
        self, get_pr, label_found, task_factory, project_config, gh_api
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this
        get_pr.return_values = None
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task.logger = mock.Mock()
        task.build_notes_label = self.BUILD_NOTES_LABEL

        generator = mock.Mock()
        label_found.return_value = True

        pull_request = ShortPullRequest(
            self._get_expected_pull_request(1, 1, "Body"), gh_api
        )
        pull_request.base.ref = "feature/cool-new-thing"
        get_pr.return_value = pull_request
        task._get_parent_pull_request = mock.Mock(return_value=pull_request)

        task._handle_branch_name_option(generator, self.BRANCH_NAME)
        assert not generator.update_unaggregated_pr_header.called
        generator.aggregate_child_change_notes.assert_called_once()

    @mock.patch("cumulusci.tasks.release_notes.task.is_label_on_pull_request")
    @mock.patch("cumulusci.tasks.release_notes.task.get_pull_requests_by_head")
    def test_handle_branch_name_option__review_label_not_found(
        self, get_pr, label_found, task_factory, project_config, gh_api
    ):
        self.init_github()
        self.project_config = project_config  # GithubApiMixin wants this
        get_pr.return_values = None
        task = task_factory(
            {
                "options": {
                    "branch_name": self.BRANCH_NAME,
                    "build_notes_label": self.BUILD_NOTES_LABEL,
                }
            }
        )
        task.logger = mock.Mock()
        task.build_notes_label = self.BUILD_NOTES_LABEL

        generator = mock.Mock()
        label_found.return_value = False

        pull_request = ShortPullRequest(
            self._get_expected_pull_request(1, 1, "Body"), gh_api
        )
        pull_request.base.ref = "feature/cool-new-thing"
        get_pr.return_value = pull_request
        task._get_parent_pull_request = mock.Mock(return_value=pull_request)

        task._handle_branch_name_option(generator, self.BRANCH_NAME)
        assert not generator.aggregate_child_change_notes.called
        generator.update_unaggregated_pr_header.assert_called_once()
