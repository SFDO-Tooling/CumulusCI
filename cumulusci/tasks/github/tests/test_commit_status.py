from datetime import datetime

import pytest
import responses

from cumulusci.core.config import OrgConfig, ServiceConfig, TaskConfig
from cumulusci.core.exceptions import DependencyLookupError
from cumulusci.tasks.github.commit_status import GetPackageDataFromCommitStatus
from cumulusci.tasks.github.tests.util_github_api import GithubApiTestMixin
from cumulusci.tests.util import create_project_config


class TestGetPackageDataFromCommitStatus(GithubApiTestMixin):
    @responses.activate
    def test_run_task(self):
        self.init_github()
        repo_response = self._get_expected_repo("TestOwner", "TestRepo")
        now = datetime.now().isoformat()
        responses.add(method=responses.GET, url=self.repo_api_url, json=repo_response)
        responses.add(
            method=responses.GET,
            url=f"{self.repo_api_url}/commits/abcdef",
            json=self._get_expected_commit("abcdef"),
        )
        responses.add(
            method=responses.GET,
            url=f"{self.repo_api_url}/commits/abcdef/status",
            json={
                "url": f"{self.repo_api_url}/abcdef/status",
                "commit_url": f"{self.repo_api_url}/abcdef",
                "repository": repo_response,
                "sha": "abcdef",
                "state": "success",
                "statuses": [
                    {
                        "context": "2gp",
                        "created_at": now,
                        "updated_at": now,
                        "description": "version_id: 04t_1",
                        "id": 1,
                        "state": "success",
                        "target_url": None,
                        "url": f"{self.repo_api_url}/statuses/abcdef",
                    }
                ],
                "total_count": 1,
            },
        )
        responses.add(
            "GET",
            "https://salesforce/services/data/v52.0/tooling/query/",
            json={
                "records": [
                    {"Dependencies": {"ids": [{"subscriberPackageVersionId": "04t_2"}]}}
                ]
            },
        )

        project_config = create_project_config(repo_commit="abcdef")
        project_config.keychain.set_service(
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
        task_config = TaskConfig({"options": {"context": "2gp"}})
        org_config = OrgConfig(
            {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
        )
        task = GetPackageDataFromCommitStatus(project_config, task_config, org_config)
        task._init_task()
        task._run_task()
        assert task.return_values == {
            "version_id": "04t_1",
            "dependencies": [{"version_id": "04t_2"}],
        }

    @responses.activate
    def test_run_task__commit_not_found(self):
        self.init_github()
        responses.add(
            method=responses.GET,
            url=self.repo_api_url,
            json=self._get_expected_repo("TestOwner", "TestRepo"),
        )
        responses.add(
            method=responses.GET, url=f"{self.repo_api_url}/commits/abcdef", status=422
        )

        project_config = create_project_config(repo_commit="abcdef")
        project_config.keychain.set_service(
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
        task_config = TaskConfig({"options": {"context": "2gp"}})
        org_config = OrgConfig(
            {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
        )
        task = GetPackageDataFromCommitStatus(project_config, task_config, org_config)
        task._init_task()
        with pytest.raises(
            DependencyLookupError,
            match="Could not find package version id in '2gp' commit status for commit abcdef.",
        ):
            task._run_task()

    @responses.activate
    def test_run_task__status_not_found(self):
        self.init_github()
        repo_response = self._get_expected_repo("TestOwner", "TestRepo")
        responses.add(method=responses.GET, url=self.repo_api_url, json=repo_response)
        responses.add(
            method=responses.GET,
            url=f"{self.repo_api_url}/commits/abcdef",
            json=self._get_expected_commit("abcdef"),
        )
        responses.add(
            method=responses.GET,
            url=f"{self.repo_api_url}/commits/abcdef/status",
            json={
                "url": f"{self.repo_api_url}/abcdef/status",
                "commit_url": f"{self.repo_api_url}/abcdef",
                "repository": repo_response,
                "sha": "abcdef",
                "state": "success",
                "statuses": [],
                "total_count": 0,
            },
        )

        project_config = create_project_config(repo_commit="abcdef")
        project_config.keychain.set_service(
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
        task_config = TaskConfig({"options": {"context": "2gp"}})
        org_config = OrgConfig(
            {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
        )
        task = GetPackageDataFromCommitStatus(project_config, task_config, org_config)
        task._init_task()
        with pytest.raises(
            DependencyLookupError,
            match="Could not find package version id in '2gp' commit status",
        ):
            task._run_task()

    @responses.activate
    def test_get_dependencies__version_not_found(self):
        responses.add(
            "GET",
            "https://salesforce/services/data/v52.0/tooling/query/",
            json={"records": []},
        )

        project_config = create_project_config(repo_commit="abcdef")
        project_config.keychain.set_service(
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
        task_config = TaskConfig({"options": {"context": "2gp"}})
        org_config = OrgConfig(
            {"instance_url": "https://salesforce", "access_token": "TOKEN"}, "test"
        )
        task = GetPackageDataFromCommitStatus(project_config, task_config, org_config)
        task._init_task()
        with pytest.raises(
            DependencyLookupError, match="Could not look up dependencies of 04t"
        ):
            task._get_dependencies("04t")
