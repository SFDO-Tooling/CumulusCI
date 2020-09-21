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
        self.repo_api_url = f"https://api.github.com/repos/{self.owner}/{self.repo}"
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

        return MergeBranch(
            project_config=self.project_config,
            task_config=TaskConfig(task_config),
            org_config=DummyOrgConfig(),
        )

    def _mock_repo(self):
        api_url = self.repo_api_url

        expected_response = self._get_expected_repo(owner=self.owner, name=self.repo)
        responses.add(method=responses.GET, url=api_url, json=expected_response)
        return expected_response

    def _mock_branch(self, branch, expected_response=None):
        api_url = f"{self.repo_api_url}/branches/{branch}"
        if not expected_response:
            expected_response = self._get_expected_branch(branch)
        responses.add(method=responses.GET, url=api_url, json=expected_response)

    def _mock_branches(self, branches=None):
        api_url = f"{self.repo_api_url}/branches"
        if branches:
            expected_response = branches
        else:
            expected_response = []

        responses.add(method=responses.GET, url=api_url, json=expected_response)
        return expected_response

    def _mock_branch_does_not_exist(self, branch):
        api_url = f"{self.repo_api_url}/branches/{branch}"
        expected_response = self._get_expected_not_found()
        responses.add(
            method=responses.GET,
            url=api_url,
            status=http.client.NOT_FOUND,  # 404
            json=expected_response,
        )

    def _mock_merge(self, status=http.client.CREATED):
        api_url = f"{self.repo_api_url}/merges"
        expected_response = self._get_expected_merge(status == http.client.CONFLICT)

        responses.add(
            method=responses.POST, url=api_url, json=expected_response, status=status
        )
        return expected_response

    def _mock_pull_create(self, pull_id, issue_id):
        api_url = f"{self.repo_api_url}/pulls"
        expected_response = self._get_expected_pull_request(pull_id, issue_id)

        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_response,
            status=http.client.CREATED,  # 201
        )

    def _mock_compare(self, base, head, files=None):
        api_url = f"{self.repo_api_url}/compare/{base}...{head}"
        expected_response = self._get_expected_compare(base, head, files)

        responses.add(method=responses.GET, url=api_url, json=expected_response)

    def _get_log_lines(self, log):
        log_lines = []
        for event in log.records:
            if event.name != "cumulusci.core.tasks":
                continue
            log_lines.append((event.levelname, event.getMessage()))
        return log_lines

    def _setup_mocks(self, branch_names, merges=True, compare_diff=True):
        """Setup all mocks needed for an integration test
        of MergeBranch with the given branch_names.
        source_branch should be at index 0
        """
        # Create response for repo endpoint
        self._mock_repo()
        # Create endpoint for repo/pulls...
        self.mock_pulls()

        # Create response for source branch endpoint
        self._mock_branch(branch_names[0])

        branch_response_bodies = []
        for name in branch_names:
            branch_response_bodies.append(self._get_expected_branch(name))

        # Create response for repo/branches endpoint
        branches = self._mock_branches(branch_response_bodies)

        if merges:
            # Create endpoint for repo/merges endpoint
            merges = [self._mock_merge()]
        # Create endpoints for repo/compare/{base}...{head}
        for branch in branches[1:]:
            files = [{"filename": "text.txt"}] if compare_diff else []
            self._mock_compare(
                base=branch["name"],
                head=self.project_config.repo_commit,
                files=files,
            )

    @responses.activate
    def test_branch_does_not_exist(self):
        self._mock_repo()
        self._mock_branch_does_not_exist(self.branch)

        task = self._create_task()
        with self.assertRaises(GithubApiNotFoundError):
            task()
        self.assertEqual(2, len(responses.calls))

    @responses.activate
    def test_no_descendents_of_main(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        other_branch = self._get_expected_branch("not-a-feature-branch")
        self.mock_pulls()
        branches = [self._get_expected_branch("main"), other_branch]
        branches = self._mock_branches(branches)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = log_header() + [
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "DEBUG",
                    "Skipping branch not-a-feature-branch: does not match prefix 'feature/'",
                ),
            ]
            self.assertEqual(expected, log_lines)
        self.assertEqual(4, len(responses.calls))

    @responses.activate
    def test_feature_branch_no_diff(self):
        self._setup_mocks(["main", "feature/a-test"], merges=False, compare_diff=False)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = log_header() + [
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
        branches.append(self._get_expected_branch("main"))
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
                ("INFO", "Merged 1 commits into branch: feature/a-test"),
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
        branches.append(self._get_expected_branch("main"))
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
        branches.append(self._get_expected_branch("main"))
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

            expected = log_header() + [
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
        branches.append(self._get_expected_branch("main"))
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

            expected = log_header() + [
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
        branches.append(self._get_expected_branch("main"))
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
        expected = log_header() + [
            ("DEBUG", "Skipping branch main: is source branch"),
            (
                "DEBUG",
                f"Skipping branch {child_branch_name}: is not a direct descendent of main",
            ),
            (
                "INFO",
                f"Merge conflict on branch {parent_branch_name}: created pull request #2",
            ),
        ]
        self.assertEqual(expected, log_lines)
        self.assertEqual(7, len(responses.calls))

    @responses.activate
    def test_main_merge_to_feature(self):
        """Tests that commits to the main branch are merged to the expected feature branches"""

        prefix = "neptune/"
        source_branch = "main"
        child_branches = [
            f"{prefix}230",
            f"{prefix}work-a",
            f"{prefix}work-b",
        ]
        other_branches = [
            "venus/work-a",
            f"{prefix}work-a__child_a",
            f"{prefix}work-a__child_a__grandchild",
            f"{prefix}work-b__child_b",
            f"{prefix}orphan__with_child",
            f"{prefix}230__cool_feature",
            f"{prefix}230__cool_feature__child",
        ]
        self._setup_mocks([source_branch] + child_branches + other_branches)

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {"source_branch": source_branch, "branch_prefix": prefix}
                }
            )
            task()

            expected_log = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", f"Skipping branch {source_branch}: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[0]}: does not match prefix '{prefix}'",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[1]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[2]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[3]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[4]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[5]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[6]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {child_branches[0]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {child_branches[1]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {child_branches[2]}",
                ),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(10, len(responses.calls))

    @responses.activate
    def test_merge_feature_to_children(self):
        """Tests that only direct descendents of a branch
        with the given branch_prefix receive merges."""

        prefix = "mars/"
        source_branch = f"{prefix}a-test"
        child_branches = [
            f"{prefix}a-test__a-child1",
            f"{prefix}a-test__a-child2",
        ]
        other_branches = [
            "main",
            "saturn/a-test__child",
            f"{prefix}a-test__a-child1__grandchild1",
            f"{prefix}a-test__a-child2__grandchild2",
        ]

        self._setup_mocks([source_branch] + child_branches + other_branches)

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": source_branch,
                        "branch_prefix": prefix,
                    }
                }
            )
            task()
            expected_log = [
                ("INFO", "Beginning task: MergeBranch"),
                ("INFO", ""),
                ("DEBUG", f"Skipping branch {source_branch}: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[0]}: does not match prefix '{prefix}'",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[1]}: does not match prefix '{prefix}'",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[2]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[3]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Found child branches to update: {[branch for branch in child_branches]}",
                ),
                ("INFO", f"Merged 1 commits into branch: {child_branches[0]}"),
                ("INFO", f"Merged 1 commits into branch: {child_branches[1]}"),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(8, len(responses.calls))

    @responses.activate
    def test_merge_feature_child_to_grandchildren(self):
        """Tests that when source branch is a child branch, we only merge
        to granchildren."""
        source_branch = "feature/test__work"
        child_branches = [
            "feature/test__work__child1",
            "feature/test__work__child2",
        ]
        other_branches = [
            "feature/test__work__child1__grandchild1",
            "feature/test__work__child2__grandchild2",
            "feature/test__workchild__2",
        ]
        self._setup_mocks([source_branch] + child_branches + other_branches)

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": source_branch,
                    }
                }
            )
            task()

            expected_log = log_header() + [
                ("DEBUG", f"Skipping branch {source_branch}: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[0]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[1]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[2]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Found child branches to update: {[branch for branch in child_branches]}",
                ),
                ("INFO", f"Merged 1 commits into branch: {child_branches[0]}"),
                ("INFO", f"Merged 1 commits into branch: {child_branches[1]}"),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(8, len(responses.calls))

    @responses.activate
    def test_feature_merge_no_children(self):
        source_branch = "feature/a-test"
        other_branch = "feature/b-test"
        self._setup_mocks([source_branch, other_branch])

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": source_branch,
                    }
                }
            )
            task()

            expected_log = log_header() + [
                ("DEBUG", "Skipping branch feature/a-test: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branch}: is not a direct descendent of {source_branch}",
                ),
                ("DEBUG", f"No children found for branch {source_branch}"),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(4, len(responses.calls))

    @responses.activate
    def test_merge_to_future_prerelease_branches(self):
        """Tests that commits to the main branch are merged to the expected feature branches"""

        prefix = "jupiter/"
        source_branch = f"{prefix}230"
        future_prereleases = [
            f"{prefix}232",
            f"{prefix}300",
            f"{prefix}980",
        ]
        other_branches = [
            f"{prefix}000",
            f"{prefix}130",
            f"{prefix}229",
        ]
        self._setup_mocks([source_branch] + future_prereleases + other_branches)

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": source_branch,
                        "branch_prefix": prefix,
                        "update_prerelease": True,
                    }
                }
            )
            task()

            expected_log = log_header() + [
                ("DEBUG", f"Skipping branch {source_branch}: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[0]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[1]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[2]}: is not a direct descendent of {source_branch}",
                ),
                ("DEBUG", "No children found for branch jupiter/230"),
                (
                    "DEBUG",
                    f"Found future prerelease branches to update: {[f'{branch}' for branch in future_prereleases]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {future_prereleases[0]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {future_prereleases[1]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {future_prereleases[2]}",
                ),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(10, len(responses.calls))

    @responses.activate
    def test_merge_to_future_prerelease_branches_and_children(self):
        """Tests that commits to the main branch are merged to the expected feature branches"""

        prefix = "jupiter/"
        source_branch = f"{prefix}230"
        branches_to_merge = [
            f"{prefix}300",
            f"{prefix}230__child1",
        ]
        other_branches = [
            f"{prefix}230__child1__grandchild",
            "prefix-mismatch/230__child2",
            f"{prefix}130",
        ]
        self._setup_mocks([source_branch] + branches_to_merge + other_branches)

        with LogCapture() as log:
            task = self._create_task(
                task_config={
                    "options": {
                        "source_branch": source_branch,
                        "branch_prefix": prefix,
                        "update_prerelease": True,
                    }
                }
            )
            task()

            expected_log = log_header() + [
                ("DEBUG", f"Skipping branch {source_branch}: is source branch"),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[0]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[1]}: does not match prefix '{prefix}'",
                ),
                (
                    "DEBUG",
                    f"Skipping branch {other_branches[2]}: is not a direct descendent of {source_branch}",
                ),
                (
                    "DEBUG",
                    f"Found child branches to update: ['{branches_to_merge[1]}']",
                ),
                (
                    "DEBUG",
                    f"Found future prerelease branches to update: ['{branches_to_merge[0]}']",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {branches_to_merge[1]}",
                ),
                (
                    "INFO",
                    f"Merged 1 commits into branch: {branches_to_merge[0]}",
                ),
            ]
            actual_log = self._get_log_lines(log)
            self.assertEqual(expected_log, actual_log)
        self.assertEqual(8, len(responses.calls))

    def test_is_prerelease_branch(self):
        prefix = "test/"
        valid_prerelease_branches = [
            f"{prefix}200",
            f"{prefix}201",
            f"{prefix}202",
            f"{prefix}202",
            f"{prefix}382",
            f"{prefix}972",
        ]
        invalid_prerelease_branches = [
            f"{prefix}000",
            f"{prefix}100",
            f"{prefix}199",
            f"{prefix}1000",
            f"{prefix}1000",
            f"{prefix}200_",
            f"{prefix}230_",
            f"{prefix}230a",
        ]
        task = self._create_task(
            task_config={
                "options": {
                    "branch_prefix": prefix,
                }
            }
        )
        for branch in valid_prerelease_branches:
            assert task._is_prerelease_branch(branch)
        for branch in invalid_prerelease_branches:
            assert not task._is_prerelease_branch(branch)


def log_header():
    return [
        ("INFO", "Beginning task: MergeBranch"),
        ("INFO", ""),
    ]
