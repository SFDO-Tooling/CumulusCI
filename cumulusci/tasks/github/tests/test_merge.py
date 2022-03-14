import http.client

import github3
import pytest
import responses
from testfixtures import LogCapture

from cumulusci.core.config import ServiceConfig, TaskConfig
from cumulusci.core.exceptions import GithubApiNotFoundError
from cumulusci.tasks.github import MergeBranch
from cumulusci.tasks.release_notes.tests.utils import MockUtilBase
from cumulusci.tests.util import DummyOrgConfig, create_project_config


class TestMergeBranch(MockUtilBase):
    def setup_method(self):

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
            "test_alias",
            ServiceConfig(
                {
                    "username": "TestUser",
                    "token": "TestPass",
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

    def _mock_pull_create(self, pull_id, issue_id, status=None):
        api_url = f"{self.repo_api_url}/pulls"
        expected_response = self._get_expected_pull_request(pull_id, issue_id)

        responses.add(
            method=responses.POST,
            url=api_url,
            json=expected_response,
            status=status or http.client.CREATED,  # 201
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
        with pytest.raises(GithubApiNotFoundError):
            task()
        assert 2 == len(responses.calls)

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
            assert expected == log_lines
        assert 3 == len(responses.calls)

    @responses.activate
    def test_feature_branch_no_diff(self):
        self._setup_mocks(["main", "feature/a-test"], merges=False, compare_diff=False)
        with LogCapture() as log:
            task = self._create_task()
            task()
            log_lines = self._get_log_lines(log)

            expected = log_header() + [
                ("DEBUG", "Skipping branch main: is source branch"),
                ("DEBUG", "Found descendents of main to update: ['feature/a-test']"),
                ("INFO", "Skipping branch feature/a-test: no file diffs found"),
            ]
            assert expected == log_lines
        assert 4 == len(responses.calls)

    @responses.activate
    def test_task_output__feature_branch_merge(self):
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
                ("DEBUG", "Found descendents of main to update: ['feature/a-test']"),
                ("INFO", "Merged 1 commits into branch: feature/a-test"),
            ]
            assert expected == log_lines
        assert 5 == len(responses.calls)

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
        with pytest.raises(github3.GitHubError):
            task()

    @responses.activate
    def test_task_output__feature_branch_merge_conflict(self):
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
            actual_log = self._get_log_lines(log)

            expected_log = log_header() + [
                ("DEBUG", "Skipping branch main: is source branch"),
                ("DEBUG", "Found descendents of main to update: ['feature/a-test']"),
                (
                    "INFO",
                    "Merge conflict on branch feature/a-test: created pull request #2",
                ),
            ]
            assert expected_log == actual_log
        assert 7 == len(responses.calls)

    @responses.activate
    def test_merge__error_on_merge_conflict_pr(self):
        self._mock_repo()
        self._mock_branch(self.branch)
        self.mock_pulls()
        # branches
        branches = []
        branches.append(self._get_expected_branch("main"))
        branches.append(self._get_expected_branch("feature/one"))
        branches = self._mock_branches(branches)
        # pull request
        pull = self._get_expected_pull_request(1, 2)
        pull["base"]["ref"] = "feature/one"
        pull["base"]["sha"] = branches[1]["commit"]["sha"]
        pull["head"]["ref"] = "main"
        self.mock_pulls(pulls=[pull])
        # compare
        self._mock_compare(
            base="feature/one",
            head=self.project_config.repo_commit,
            files=[{"filename": "test.txt"}],
        )
        # merge
        self._mock_merge(http.client.CONFLICT)
        # merge conflict PR to return exception
        self._mock_pull_create(8, 8, status=http.client.UNPROCESSABLE_ENTITY)
        with LogCapture() as log:
            task = self._create_task()
            task._init_task()
            task._merge("feature/one", "main", self.project_config.repo_commit)
            actual_log = self._get_log_lines(log)

        assert actual_log[0][0] == "ERROR"
        assert actual_log[0][1].startswith(
            "Error creating merge conflict pull request to merge main into feature/one:\n"
        )

    @responses.activate
    def test_task_output__feature_branch_existing_pull(self):
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
                ("DEBUG", "Found descendents of main to update: ['feature/a-test']"),
                (
                    "INFO",
                    "Merge conflict on branch feature/a-test: merge PR already exists",
                ),
            ]
            assert expected == log_lines
        assert 6 == len(responses.calls)

    @responses.activate
    def test_task_output__main_parent_with_child_pr(self):
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
            actual_log = self._get_log_lines(log)
        expected_log = log_header() + [
            ("DEBUG", "Skipping branch main: is source branch"),
            (
                "DEBUG",
                "Skipping branch feature/a-test__a-child: is not a direct descendent of main",
            ),
            ("DEBUG", "Found descendents of main to update: ['feature/a-test']"),
            (
                "INFO",
                "Merge conflict on branch feature/a-test: created pull request #2",
            ),
        ]
        assert expected_log == actual_log
        assert 7 == len(responses.calls)

    @responses.activate
    def test_task_output__main_merge_to_feature(self):
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

            expected_log = log_header() + [
                ("DEBUG", "Skipping branch main: is source branch"),
                (
                    "DEBUG",
                    "Skipping branch venus/work-a: does not match prefix 'neptune/'",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/work-a__child_a: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/work-a__child_a__grandchild: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/work-b__child_b: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/orphan__with_child: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/230__cool_feature: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Skipping branch neptune/230__cool_feature__child: is not a direct descendent of main",
                ),
                (
                    "DEBUG",
                    "Found descendents of main to update: ['neptune/230', 'neptune/work-a', 'neptune/work-b']",
                ),
                (
                    "INFO",
                    "Merged 1 commits into branch: neptune/230",
                ),
                (
                    "INFO",
                    "Merged 1 commits into branch: neptune/work-a",
                ),
                (
                    "INFO",
                    "Merged 1 commits into branch: neptune/work-b",
                ),
            ]
            actual_log = self._get_log_lines(log)
            assert expected_log == actual_log
        assert 9 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__main_to_feature_and_next_release(self):
        """Tests that when main branch is the source_branch
        that all expected child branches and the *lowest numbered*
        release branch are merged into."""

        self._setup_mocks(
            [
                "main",
                "feature/230",
                "feature/340",
                "feature/450",
                "feature/work-a",
                "feature/work-b",
                "feature/work-a__child_a",
                "feature/work-a__child_a__grandchild",
                "feature/work-b__child_b",
                "feature/orphan__with_child",
                "feature/230__cool_feature",
                "feature/230__cool_feature__child",
            ]
        )

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "main",
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        expected_branches_to_merge = [
            "feature/230",
            "feature/work-a",
            "feature/work-b",
        ]
        assert expected_branches_to_merge == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__no_prefix_merge_to_feature(self):
        """Tests that when source_branch is a branch other than main
        and doesn't start with 'feature/', that it is merged
        to all non-child feature/ branches"""

        source_branch = "some-branch"
        expected_branches_to_merge = ["feature/work-a", "feature/work-b"]
        other_branches = [
            "feature/work-a__child",
            "some-branch__child",
            "main",
        ]
        self._setup_mocks([source_branch] + expected_branches_to_merge + other_branches)

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": source_branch,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        assert expected_branches_to_merge == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__merge_feature_to_children(self):
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

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": source_branch,
                    "branch_prefix": prefix,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        assert child_branches == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__merge_feature_child_to_grandchildren(self):
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

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": source_branch,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        assert child_branches == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__feature_merge_no_children(self):
        source_branch = "feature/a-test"
        other_branch = "feature/b-test"
        self._setup_mocks([source_branch, other_branch])

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": source_branch,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]

        assert [] == actual_branches
        # First API call is task.get_repo() (above)
        # Second API call is to self.repo.branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_merge_to_future_release_branches(self):
        """Tests that commits to the main branch are merged to the expected feature branches"""
        self._setup_mocks(
            ["main", "feature/230", "feature/232", "feature/300", "feature/work-item"]
        )

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "feature/230",
                    "branch_prefix": "feature/",
                    "update_future_releases": True,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]

        assert ["feature/232", "feature/300"] == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_merge_to_future_release_branches_missing_slash(self):
        """Tests that commits to the main branch are merged to the expected feature branches"""
        self._setup_mocks(
            [
                "main",
                "prefix-no-slash230",
                "prefix-no-slash232",
                "prefix-no-slash300",
                "prefix-no-slashwork-item",
            ]
        )

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "prefix-no-slash230",
                    "branch_prefix": "prefix-no-slash",
                    "update_future_releases": True,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]

        assert ["prefix-no-slash232", "prefix-no-slash300"] == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__future_release_branches_and_children(self):
        """Tests that commits to the upcoming release branch
        are merged to future release branches and direct child descendents."""

        self._setup_mocks(
            [
                "feature/230",
                "feature/300",
                "feature/400",
                "feature/230__child1",
                "feature/230__child1__grandchild",
                "prefix-mismatch/230__child2",
            ]
        )

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "feature/230",
                    "branch_prefix": "feature/",
                    "update_future_releases": True,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        assert ["feature/230__child1", "feature/300", "feature/400"] == actual_branches
        assert 2 == len(responses.calls)

    @responses.activate
    def test_merge_to_children_not_future_releases_output(self):
        """Tests that commits to the main branch are merged to child feature branches
        and not to future prerelease branches."""

        prefix = "jupiter/"
        source_branch = f"{prefix}230"
        branch_to_merge = f"{prefix}230__child1"
        other_branches = [
            f"{prefix}300",
            f"{prefix}230__child1__grandchild",
            "prefix-mismatch/230__child2",
            f"{prefix}130",
        ]
        self._setup_mocks([source_branch, branch_to_merge] + other_branches)

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

            expected_log = log_header() + [
                ("DEBUG", "Skipping branch jupiter/230: is source branch"),
                (
                    "DEBUG",
                    "Skipping branch jupiter/300: is not a direct descendent of jupiter/230",
                ),
                (
                    "DEBUG",
                    "Skipping branch jupiter/230__child1__grandchild: is not a direct descendent of jupiter/230",
                ),
                (
                    "DEBUG",
                    "Skipping branch prefix-mismatch/230__child2: does not match prefix 'jupiter/'",
                ),
                (
                    "DEBUG",
                    "Skipping branch jupiter/130: is not a direct descendent of jupiter/230",
                ),
                (
                    "DEBUG",
                    "Found child branches to update: ['jupiter/230__child1']",
                ),
                (
                    "INFO",
                    "Merged 1 commits into branch: jupiter/230__child1",
                ),
            ]
            actual_log = self._get_log_lines(log)
            assert expected_log == actual_log
        assert 5 == len(responses.calls)

    @responses.activate
    def test_branches_to_merge__children_not_future_releases(self):
        """Tests that commits to the main branch are merged to child feature branches
        and not to future prerelease branches."""

        prefix = "jupiter/"
        source_branch = f"{prefix}230"
        branch_to_merge = f"{prefix}230__child"
        other_branches = [
            f"{prefix}300",
            f"{prefix}230__child__grandchild",
            "prefix-mismatch/230__child2",
            f"{prefix}130",
        ]
        self._setup_mocks([source_branch, branch_to_merge] + other_branches)

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": source_branch,
                    "branch_prefix": prefix,
                }
            }
        )
        task._init_task()

        actual_branches = [branch.name for branch in task._get_branches_to_merge()]
        expected_branches = ["jupiter/230__child"]

        assert expected_branches == actual_branches
        assert 2 == len(responses.calls)

    def test_is_release_branch(self):
        prefix = "test/"
        valid_release_branches = [
            f"{prefix}000",
            f"{prefix}100",
            f"{prefix}199",
            f"{prefix}230",
            f"{prefix}20302",
            f"{prefix}3810102",
            f"{prefix}9711112",
        ]
        invalid_release_branches = [
            f"{prefix}200_",
            f"{prefix}_200" f"{prefix}230_",
            f"{prefix}230__child",
            f"{prefix}230__grand__child",
            f"{prefix}230a",
            f"{prefix}r1",
            f"{prefix}R1",
        ]
        task = self._create_task(
            task_config={
                "options": {
                    "branch_prefix": prefix,
                }
            }
        )
        for branch in valid_release_branches:
            assert task._is_release_branch(branch)
        for branch in invalid_release_branches:
            assert not task._is_release_branch(branch)

    @responses.activate
    def test_set_next_release(self):
        """Tests that the method sets _next_release as
        the lowest number that corresponds to a release branch"""
        self._setup_mocks(
            [
                "main",
                "feature/300",
                "feature/230",
                "feature/230__child__grandchild",
                "feature/88",
                "prefix-mismatch/230__child2",
                "feature/130",
                "feature/131",
                "f/33",
                "featurette/20",
                "features/15",
            ]
        )

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "main",
                    "branch_prefix": "feature/",
                }
            }
        )
        task._init_task()

        repo_branches = list(task.repo.branches())
        assert task._get_next_release(repo_branches) == 88

    @responses.activate
    def test_is_future_release_branch(self):
        """Tests whether the given branch name
        is a release branch that is occurring after
        the next release."""

        self._setup_mocks(["feature/8"])

        task = self._create_task(
            task_config={
                "options": {
                    "source_branch": "main",
                    "branch_prefix": "feature/",
                }
            }
        )
        task._init_task()

        repo_branches = list(task.repo.branches())
        assert task._get_next_release(repo_branches) == 8

        assert not task._is_future_release_branch("f", 8)
        assert not task._is_future_release_branch("feature", 8)
        assert not task._is_future_release_branch("feature/", 8)
        assert not task._is_future_release_branch("feature/_", 8)
        assert not task._is_future_release_branch("feature/0", 8)
        assert not task._is_future_release_branch("feature/O", 8)
        assert not task._is_future_release_branch("feature/7", 8)
        assert not task._is_future_release_branch("feature/8", 8)
        assert not task._is_future_release_branch("feature/9_", 8)

        assert task._is_future_release_branch("feature/9", 8)
        assert task._is_future_release_branch("feature/75", 8)
        assert task._is_future_release_branch("feature/123", 8)
        assert task._is_future_release_branch("feature/4567", 8)
        assert task._is_future_release_branch("feature/10000", 8)


def log_header():
    return [
        ("INFO", "Beginning task: MergeBranch"),
        ("INFO", ""),
    ]
