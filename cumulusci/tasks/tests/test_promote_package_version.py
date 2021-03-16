import logging
import pytest
import responses
from unittest import mock

from cumulusci.core.config import TaskConfig, BaseProjectConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce.promote_package_version import PromotePackageVersion


@pytest.fixture
def project_config():
    project_config = BaseProjectConfig(UniversalConfig())
    project_config.keychain = BaseProjectKeychain(project_config, key=None)
    return project_config


@pytest.fixture
def task(project_config, devhub_config, org_config):
    task = PromotePackageVersion(
        project_config,
        TaskConfig(
            {
                "options": {
                    "version_id": "04t000000000000",
                    "auto_promote": False,
                }
            }
        ),
        org_config,
    )
    with mock.patch(
        "cumulusci.tasks.salesforce.promote_package_version.get_devhub_config",
        return_value=devhub_config,
    ):
        task._init_task()
    return task


class TestPromotePackageVersion:
    devhub_base_url = "https://devhub.my.salesforce.com/services/data/v50.0"

    def _mock_dependencies(
        self, total_deps: int, num_2gp: int, num_unpromoted: int
    ) -> None:
        """
        Mock all API calls to represent the dependencies requested in params

        @param total_deps: total number of dependencies to mock
        @param num_2gp: number of 2GP dependencies (all others will be 1GP)
        @param num_unpromoted: of the num_2gp packages, how many are not yet promoted
        """
        spv_ids = [
            {"subscriberPackageVersionId": f"04t00000000000{i + 1}"}
            for i in range(total_deps)
        ]
        responses.add(  # query to find dependency packages
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Dependencies": {"ids": spv_ids}}],
                "done": True,
            },
        )
        # mock 1GP dependencies
        for i in range(total_deps - num_2gp):
            self._mock_dependency(i + 1, is_two_gp=False)

        # mock unpromoted 2GP dependencies
        for i in range(num_unpromoted):
            self._mock_dependency(i + 1, is_two_gp=True)

        # mock promoted 2GP dependencies
        for i in range(num_2gp - num_unpromoted):
            self._mock_dependency(i + 1, is_two_gp=True, is_promoted=True)

        responses.add(  # query for main package's Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "main_package", "IsReleased": False}],
                "done": True,
            },
        )
        responses.add(
            "PATCH",
            f"{self.devhub_base_url}/tooling/sobjects/Package2Version/main_package",
        )

    def _mock_dependency(
        self, dependency_num: int, is_two_gp: bool = False, is_promoted: bool = False
    ) -> None:
        """Mock the API calls for a single dependency"""
        responses.add(  # query for SubscriberPackageVersion
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "SubscriberPackageId": str(dependency_num),
                        "ReleaseState": "Released" if is_promoted else "Beta",
                    }
                ],
                "done": True,
            },
        )
        responses.add(  # query for SubscriberPackage
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Name": f"Dependency_Package_{dependency_num}"}],
                "done": True,
            },
        )

        one_gp_json = {"size": 0, "records": [], "done": True}
        two_gp_json = {
            "size": 1,
            "records": [{"Id": f"dep_{dependency_num}", "IsReleased": False}],
            "done": True,
        }
        responses.add(  # query for Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json=(two_gp_json if is_two_gp else one_gp_json),
        )

        if is_two_gp:
            responses.add(
                "PATCH",
                f"{self.devhub_base_url}/tooling/sobjects/Package2Version/dep_{dependency_num}",
            )

    def test_run_task__no_version_id(self, project_config, devhub_config, org_config):
        with pytest.raises(
            TaskOptionsError, match="Task option `version_id` is required."
        ):
            PromotePackageVersion(
                project_config,
                TaskConfig({"options": {}}),
                org_config,
            )

    def test_run_task__invalid_version_id(
        self, project_config, devhub_config, org_config
    ):
        with pytest.raises(TaskOptionsError):
            PromotePackageVersion(
                project_config,
                TaskConfig({"options": {"version_id": "0Ho000000000000"}}),
                org_config,
            )

    @responses.activate
    def test_run_task(self, task, devhub_config):
        # 20 dependencies, 10 are 2GP, 5 of those are not yet promoted
        self._mock_dependencies(20, 10, 5)
        with mock.patch(
            "cumulusci.tasks.salesforce.promote_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

    @responses.activate
    def test_run_task__no_dependencies(self, task, devhub_config):
        self._mock_dependencies(0, 0, 0)
        with mock.patch(
            "cumulusci.tasks.salesforce.promote_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

    @responses.activate
    def test_run_task__promote_dependencies(self, task, devhub_config):
        self._mock_dependencies(2, 1, 1)
        with mock.patch(
            "cumulusci.tasks.salesforce.promote_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task.options["promote_dependencies"] = True
            task()

    @responses.activate
    def test_run_task__all_deps_promoted(self, task, devhub_config):
        self._mock_dependencies(4, 4, 4)
        with mock.patch(
            "cumulusci.tasks.salesforce.promote_package_version.get_devhub_config",
            return_value=devhub_config,
        ):
            task.options["auto_promote"] = True
            task()

    def test_process_one_gp_dependencies(self, task, caplog):
        """Ensure proper logging output"""
        dependencies = [
            {
                "is_2gp": False,
                "name": "Dependency 1",
                "release_state": "Beta",
                "version_id": "04t000000000001",
            },
            {
                "is_2gp": True,
                "name": "Dependency 2",
                "release_state": "Beta",
                "version_id": "04t000000000002",
            },
        ]
        task._process_one_gp_deps(dependencies)
        assert (
            "This package has the following 1GP dependencies:"
            == caplog.records[0].message
        )
        assert "Package Name: Dependency 1" in caplog.records[2].message
        assert "Release State: Beta" in caplog.records[3].message
        assert (
            "SubscriberPackageVersionId: 04t000000000001" in caplog.records[4].message
        )

    def test_process_two_gp_dependencies(self, task, caplog):
        """Ensure proper logging output"""
        dependencies = [
            {"is_2gp": False, "name": "Dependency 1", "release_state": "Beta"},
            {
                "is_2gp": True,
                "name": "Dependency 2",
                "release_state": "Beta",
                "is_promoted": False,
                "version_id": "04t000000000002",
            },
        ]
        with caplog.at_level(logging.INFO):
            task._process_two_gp_deps(dependencies)
        assert "Total 2GP dependencies: 1" == caplog.records[0].message
        assert "Unpromoted 2GP dependencies: 1" == caplog.records[1].message
        assert (
            "This package depends on other packages that have not yet been promoted."
            == caplog.records[3].message
        )
        assert "Package Name: Dependency 2" in caplog.records[7].message

    @responses.activate
    def test_query_Package2Version__malformed_request(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json=[{"message": "Object type 'Package2' is not supported"}],
            status=400,
        )
        with pytest.raises(TaskOptionsError):
            task._query_Package2Version("04t000000000000")

    @responses.activate
    def test_query_one_tooling(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 2,
                "records": [{"name": "Thing_1"}, {"name": "Thing_2"}],
                "done": True,
            },
        )
        obj = task._query_one_tooling(["name"], "sObjectName")
        assert not isinstance(obj, list)

    @responses.activate
    def test_query_tooling__return_none(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": [], "done": True},
        )
        result = task._query_tooling(["Id", "name"], "sObjectName")
        assert result is None

    @responses.activate
    def test_query_tooling__return_multiple(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 2,
                "records": [{"name": "Thing_1"}, {"name": "Thing_2"}],
                "done": True,
            },
        )
        result = task._query_tooling(["Id", "name"], "sObjectName")
        assert isinstance(result, list)
        assert len(result) == 2

    @responses.activate
    def test_query_tooling__raise_error(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": [], "done": True},
        )
        with pytest.raises(
            CumulusCIException,
            match="No records returned for query: SELECT Id, Field__c FROM sObjectName WHERE Id='12345'",
        ):
            task._query_tooling(
                ["Id", "Field__c"], "sObjectName", "Id='12345'", raise_error=True
            )
