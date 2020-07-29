import http.client
import unittest

from testfixtures import LogCapture
from github3 import GitHubError
import responses

from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github import MergeBranch
from cumulusci.tasks.release_notes.tests.utils import MockUtil
from cumulusci.tests.util import create_project_config
from cumulusci.tests.util import DummyOrgConfig


class TestMergeBranch(unittest.TestCase, MockUtil):
    def setUp(self):

        # Set up the mock values
        self.repo = "TestRepo"
        self.owner = "TestOwner"
        self.repo_api_url = "https://api.github.com/repos/{}/{}".format(
            self.owner, self.repo
        )
        self.branch = "main"

        # Create the project config
        self.project_config = create_project_config(self.repo, self.owner)
        self.project_config.config["project"]["git"]["default_branch"] = self.branch
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

    def _create_task(self, task_config=None):
        if not task_config:

            task_config = {}
        task = MergeBranch(
            project_config=self.project_config,
            task_config=TaskConfig(task_config),
            org_config=DummyOrgConfig(),
        )
        return task

    def _mock_repo(self):
        api_url = self.repo_api_url

        expected_response = self._get_expected_repo(owner=self.owner, name=self.repo)
        responses.add(method=responses.GET, url=api_url, json=expected_response)
        return expected_response

    def _mock_branch(self, branch, expected_response=None):
        api_url = "{}/branches/{}".format(self.repo_api_url, branch)
        if not expected_response:
            expected_response = self._get_expected_branch(branch)
        responses.add(method=responses.GET, url=api_url, json=expected_response)

    def _mock_branches(self, branches=None):
        api_url = "{}/branches".format(self.repo_api_url)
        if branches:
            expected_response = branches
        else:
            expected_response = []

        default_branch = self._get_expected_branch(
            "main", self.project_config.repo_commit
        )
        expected_response = [default_branch] + expected_response

        responses.add(method=responses.GET, url=api_url, json=expected_response)
        return expected_response

    def _mock_branch_does_not_exist(self, branch):
        api_url = "{}/branches/{}".format(self.repo_api_url, branch)
        expected_response = self._get_expected_not_found()
        responses.add(
            method=responses.GET,
            url=api_url,
            status=http.client.NOT_FOUND,  # 404
            json=expected_response,
        )

    def _mock_merge(self, status=http.client.CREATED):
        api_url = "{}/merges".format(self.repo_api_url)
        expected_response = self._get_expected_merge(status == http.client.CONFLICT)

        responses.add(
            method=responses.POST, url=api_url, json=expected_response, status=status
        )
        return expected_response

    def _mock_pull_create(self, pull_id, issue_id):
        api_url = "{}/pulls".format(self.repo_api_url)
        expected_response = self._get_expected_pull_request(pull_id, issue_id)

        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_response,
            status=http.client.CREATED,  # 201
        )

    def _mock_compare(self, base, head, files=None):
        api_url = "{}/compare/{}...{}".format(self.repo_api_url, base, head)
        expected_response = self._get_expected_compare(base, head, files)

        responses.add(method=responses.GET, url=api_url, json=expected_response)

    def _get_log_lines(self, log):
        log_lines = []
        for event in log.records:
            if event.name != "cumulusci.core.tasks":
                continue
            log_lines.append((event.levelname, event.getMessage()))
        return log_lines

    @responses.activate
    def test_branch_does_not_exist(self):
        self._mock_repo()
        self._mock_branch_does_not_exist(self.branch)

        task = self._create_task()
        with self.assertRaises(GithubApiNotFoundError):
            task()
        self.assertEqual(2, len(responses.calls))

    @responses.activate
    def test_no_feature_branch(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        other_branch = self._get_expected_branch("not-a-feature-branch")
        self.mock_pulls()
        branches = [other_branch]
        branches = self._mock_branches(branches)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "DEBUG",
                    "Skipping branch not-a-feature-branch: does not match prefix feature/",
                ),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(4, len(responses.calls))

    @responses.activate
    def test_feature_branch_no_diff(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self.mock_pulls()
        branch_name = "feature/a-test"
        branches = []
        branches.append(self._get_expected_branch(branch_name))
        branches = self._mock_branches(branches)
        self._mock_compare(
            base=branches[1]["name"], head=self.project_config.repo_commit
        )
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                ("INFO", "Skipping branch feature/a-test: no file diffs found"),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(5, len(responses.calls))

    @responses.activate
    def test_feature_branch_merge(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self.mock_pulls()
        branch_name = "feature/a-test"
        branches = []
        branches.append(self._get_expected_branch(branch_name))
        branches = self._mock_branches(branches)
        self._mock_compare(
            base=branches[1]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        self._mock_merge()
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                ("INFO", "Merged 1 commits into branch feature/a-test"),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(6, len(responses.calls))

    @responses.activate
    def test_feature_branch_merge_github_error(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self.mock_pulls()
        branch_name = "feature/a-test"
        branches = []
        branches.append(self._get_expected_branch(branch_name))
        branches = self._mock_branches(branches)
        self._mock_compare(
            base=branches[1]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        self._mock_merge(http.client.INTERNAL_SERVER_ERROR)
        task = self._create_task()
        with self.assertRaises(GitHubError):
            task()

    @responses.activate
    def test_feature_branch_merge_conflict(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self.mock_pulls()
        branch_name = "feature/a-test"
        branches = []
        branches.append(self._get_expected_branch(branch_name))
        branches = self._mock_branches(branches)
        self._mock_compare(
            base=branches[1]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        self._mock_merge(http.client.CONFLICT)
        self._mock_pull_create(1, 2)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "INFO",
                    "Merge conflict on branch feature/a-test: created pull request #2",
                ),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(7, len(responses.calls))

    @responses.activate
    def test_feature_branch_existing_pull(self):
        self._mock_repo()
        self._mock_branch(self.branch)

        branch_name = "feature/a-test"
        branches = []
        branches.append(self._get_expected_branch(branch_name))
        branches = self._mock_branches(branches)

        pull = self._get_expected_pull_request(1, 2)
        pull["base"]["ref"] = branch_name
        pull["base"]["sha"] = branches[1]["commit"]["sha"]
        pull["head"]["ref"] = self.branch
        self.mock_pulls(pulls=[pull])

        self._mock_compare(
            base=branches[1]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        self._mock_merge(http.client.CONFLICT)

        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "INFO",
                    "Merge conflict on branch feature/a-test: merge PR already exists",
                ),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(6, len(responses.calls))

    @responses.activate
    def test_main_parent_with_child_pr(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        # branches
        parent_branch_name = "feature/a-test"
        child_branch_name = "feature/a-test__a-child"
        branches = []
        branches.append(self._get_expected_branch(parent_branch_name))
        branches.append(self._get_expected_branch(child_branch_name))
        branches = self._mock_branches(branches)
        # pull request
        pull = self._get_expected_pull_request(1, 2)
        pull["base"]["ref"] = parent_branch_name
        pull["base"]["sha"] = branches[1]["commit"]["sha"]
        pull["head"]["ref"] = child_branch_name
        self.mock_pulls(pulls=[pull])
        # compare
        self._mock_compare(
            base=parent_branch_name,
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        # merge
        self._mock_merge(http.client.CONFLICT)
        # create PR
        self._mock_pull_create(1, 2)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)
        expected = [
            ("INFO", "Beginning task: MergeBranch"),
            ("INFO", ""),
            ("DEBUG", "Skipping branch main: is source branch"),
            (
                "INFO",
                "Merge conflict on parent branch {}: created pull request #2".format(
                    parent_branch_name
                ),
            ),
        ]
        self.assertEqual(expected, log_lines)
        self.assertEqual(7, len(responses.calls))

    @responses.activate
    def test_main_parent_does_not_merge_child(self):
        self._mock_repo()
        self._mock_branch(self.branch)

        parent_branch_name = "feature/a-test"
        child1_branch_name = "feature/a-test__a-child1"
        child2_branch_name = "feature/a-test__a-child2"
        branches = []
        branches.append(self._get_expected_branch(parent_branch_name))
        branches.append(self._get_expected_branch(child1_branch_name))
        branches.append(self._get_expected_branch(child2_branch_name))
        branches = self._mock_branches(branches)

        self.mock_pulls()

        self._mock_compare(
            base=branches[1]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        merges = []
        merges.append(self._mock_merge())

        with LogCapture() as log:
            task = self._create_task()
            task()

            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "INFO",
                    "Merged 1 commits into parent branch {}".format(parent_branch_name),
                ),
                ("INFO", "  Skipping merge into the following child branches:"),
                ("INFO", "    {}".format(child1_branch_name)),
                ("INFO", "    {}".format(child2_branch_name)),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(6, len(responses.calls))

    @responses.activate
    def test_parent_merge_to_children(self):
        branch = "feature/a-test"
        self._mock_repo()
        self._mock_branch(branch)

        parent_branch_name = "feature/a-test"
        child1_branch_name = "feature/a-test__a-child1"
        child2_branch_name = "feature/a-test__a-child2"
        branches = []
        branches.append(self._get_expected_branch(parent_branch_name))
        branches.append(self._get_expected_branch(child1_branch_name))
        branches.append(self._get_expected_branch(child2_branch_name))
        branches = self._mock_branches(branches)

        self.mock_pulls()

        merges = []
        merges.append(self._mock_merge())

        self._mock_compare(
            base=branches[2]["name"],
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        self._mock_compare(
            base=branches[3]["name"], head=self.project_config.repo_commit, files=[]
        )

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": "feature/a-test",
                        "children_only": True,
                    }
                }
            )
            task()

            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                (
                    "INFO",
                    "Performing merge from parent branch {} to children".format(
                        branches[1]["name"]
                    ),
                ),
                (
                    "INFO",
                    "Merged 1 commits into child branch {}".format(branches[2]["name"]),
                ),
                (
                    "INFO",
                    "Skipping child branch {}: no file diffs found".format(
                        branches[3]["name"]
                    ),
                ),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(7, len(responses.calls))

    @responses.activate
    def test_parent_merge_no_children(self):
        branch = "feature/a-test"
        self._mock_repo()
        self._mock_branch(branch)

        parent_branch_name = "feature/a-test"
        child1_branch_name = "feature/b-test"
        branches = []
        branches.append(self._get_expected_branch(parent_branch_name))
        branches.append(self._get_expected_branch(child1_branch_name))
        branches = self._mock_branches(branches)

        self.mock_pulls()

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": "feature/a-test",
                        "children_only": True,
                    }
                }
            )
            task()

            log_lines = self._get_log_lines(log)

            expected = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("INFO", "No children found for branch {}".format(branches[1]["name"])),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(4, len(responses.calls))
