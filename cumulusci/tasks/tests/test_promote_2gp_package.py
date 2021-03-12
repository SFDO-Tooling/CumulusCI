import pytest
import responses
from unittest import mock

from cumulusci.core.config import TaskConfig, BaseProjectConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.tasks.salesforce.promote_2gp_package import Promote2gpPackageVersion


@pytest.fixture
def project_config():
    project_config = BaseProjectConfig(UniversalConfig())
    project_config.keychain = BaseProjectKeychain(project_config, key=None)
    return project_config


@pytest.fixture
def task(project_config, devhub_config, org_config):
    task = Promote2gpPackageVersion(
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
        "cumulusci.tasks.salesforce.promote_2gp_package.get_devhub_config",
        return_value=devhub_config,
    ):
        task._init_task()
    return task


class TestPromote2gpPackageVersion:
    devhub_base_url = "https://devhub.my.salesforce.com/services/data/v50.0"

    def mock_get_package_name_api_calls(self, sp_id: str, name: str) -> None:
        """Mock calls needed for _get_package_name()"""
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"SubscriberPackageId": sp_id}],
            },
        )
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Name": name}],
            },
        )

    def test_run_task__no_version_id(self, project_config, devhub_config, org_config):
        with pytest.raises(
            TaskOptionsError, match="Task option `version_id` is required."
        ):
            Promote2gpPackageVersion(
                project_config,
                TaskConfig({"options": {}}),
                org_config,
            )

    def test_run_task__invalid_version_id(
        self, project_config, devhub_config, org_config
    ):
        with pytest.raises(TaskOptionsError):
            Promote2gpPackageVersion(
                project_config,
                TaskConfig({"options": {"version_id": "0Ho000000000000"}}),
                org_config,
            )

    @responses.activate
    def test_run_task(self, task, devhub_config):
        # _get_dependency_spv_ids()
        responses.add(  # query to find dependency packages
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Dependencies": {
                            "ids": [
                                {"subscriberPackageVersionId": "04t000000000001"},
                                {"subscriberPackageVersionId": "04t000000000002"},
                            ]
                        }
                    }
                ],
            },
        )
        # _filter_1gp_deps()
        responses.add(  # query for first dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "dep1", "IsReleased": False}],
            },
        )
        responses.add(  # query for second dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        responses.add(  # query for second dep spv releaseState
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"ReleaseState": "Beta"}],
            },
        )
        # _filter_1gp_deps() --> _get_package_name()
        self.mock_get_package_name_api_calls("000000000000002", "Dependency 2")
        # _filter_unpromoted_2gp_dependencies() --> _is_package_version_promoted()
        responses.add(  # query for Package2Version for dependency 1
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"IsReleased": True}],
            },
        )
        responses.add(  # query for Package2Version for dependency 2
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        # _promote_2gp_package()
        responses.add(  # query for Package2Version to get Id
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "000000000000000"}],
            },
        )
        # _promote_2gp_package() --> _get_package_name()
        self.mock_get_package_name_api_calls("04t000000000000", "Main Package")
        responses.add(  # promote Package2Version
            "PATCH",
            f"{self.devhub_base_url}/tooling/sobjects/Package2Version/000000000000000",
        )

        with mock.patch(
            "cumulusci.tasks.salesforce.promote_2gp_package.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

    @responses.activate
    def test_run_task__unpromoted_dependencies(self, task, devhub_config):
        # _get_dependency_spv_ids()
        responses.add(  # query to find dependency packages
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Dependencies": {
                            "ids": [
                                {"subscriberPackageVersionId": "04t000000000001"},
                                {"subscriberPackageVersionId": "04t000000000002"},
                            ]
                        }
                    }
                ],
            },
        )
        # _filter_1gp_deps()
        responses.add(  # query for first dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "dep1", "IsReleased": False}],
            },
        )
        responses.add(  # query for second dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        responses.add(  # query for second dep spv releaseState
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"ReleaseState": "Beta"}],
            },
        )
        # _filter_1gp_deps() --> _get_package_name()
        self.mock_get_package_name_api_calls("000000000000002", "Dependency 2")
        # _filter_unpromoted_2gp_dependencies() --> _is_package_version_promoted()
        responses.add(  # query for Package2Version for dependency 1
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"IsReleased": False}],
            },
        )
        responses.add(  # query for Package2Version for dependency 2
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        # _filter_unpromoted_2gp_dependencies() --> _get_package_name()
        self.mock_get_package_name_api_calls("000000000000001", "Dependency 1")

        with mock.patch(
            "cumulusci.tasks.salesforce.promote_2gp_package.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

    @responses.activate
    def test_run_task__autopromote_dependencies(self, task, devhub_config):
        task.options["auto_promote"] = True

        # _get_dependency_spv_ids()
        responses.add(  # query to find dependency packages
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [
                    {
                        "Dependencies": {
                            "ids": [
                                {"subscriberPackageVersionId": "04t000000000001"},
                                {"subscriberPackageVersionId": "04t000000000002"},
                            ]
                        }
                    }
                ],
            },
        )
        # _filter_1gp_deps()
        responses.add(  # query for first dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "dep1", "IsReleased": False}],
            },
        )
        responses.add(  # query for second dependency Package2Version
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        responses.add(  # query for second dep spv releaseState
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"ReleaseState": "Beta"}],
            },
        )
        # _filter_1gp_deps() --> _get_package_name()
        self.mock_get_package_name_api_calls("000000000000002", "Dependency 2")
        # _filter_unpromoted_2gp_dependencies() --> _is_package_version_promoted()
        responses.add(  # query for Package2Version for dependency 1
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"IsReleased": False}],
            },
        )
        responses.add(  # query for Package2Version for dependency 2
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 0,
                "records": [],
            },
        )
        # _filter_unpromoted_2gp_dependencies() --> _get_package_name()
        self.mock_get_package_name_api_calls("000000000000001", "Dependency 1")

        # _promote_2gp_package (for Dependency 1)
        responses.add(  # query for Package2Version to get Id
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "000000000000001"}],
            },
        )
        # _promote_2gp_package() --> _get_package_name()
        self.mock_get_package_name_api_calls("04t000000000001", "Dependency 1")
        responses.add(  # promote Package2Version (Dependency 1)
            "PATCH",
            f"{self.devhub_base_url}/tooling/sobjects/Package2Version/000000000000001",
        )
        # _promote_2gp_package (for Main Package)
        responses.add(  # query for Package2Version to get Id
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={
                "size": 1,
                "records": [{"Id": "000000000000000"}],
            },
        )
        # _promote_2gp_package() --> _get_package_name()
        self.mock_get_package_name_api_calls("04t000000000000", "Main Package")
        responses.add(  # promote Package2Version (Dependency 1)
            "PATCH",
            f"{self.devhub_base_url}/tooling/sobjects/Package2Version/000000000000000",
        )

        with mock.patch(
            "cumulusci.tasks.salesforce.promote_2gp_package.get_devhub_config",
            return_value=devhub_config,
        ):
            task()

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
            json={"size": 2, "records": [{"name": "Thing_1"}, {"name": "Thing_2"}]},
        )
        obj = task._query_one_tooling(["name"], "sObjectName")
        assert not isinstance(obj, list)

    @responses.activate
    def test_query_tooling__return_none(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": []},
        )
        result = task._query_tooling(["Id", "name"], "sObjectName")
        assert result is None

    @responses.activate
    def test_query_tooling__return_multiple(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 2, "records": [{"name": "Thing_1"}, {"name": "Thing_2"}]},
        )
        result = task._query_tooling(["Id", "name"], "sObjectName")
        assert isinstance(result, list)
        assert len(result) == 2

    @responses.activate
    def test_query_tooling__raise_error(self, task):
        responses.add(
            "GET",
            f"{self.devhub_base_url}/tooling/query/",
            json={"size": 0, "records": []},
        )
        with pytest.raises(
            CumulusCIException,
            match="No records returned for query: SELECT Id, Field__c FROM sObjectName WHERE Id='12345'",
        ):
            task._query_tooling(
                ["Id", "Field__c"], "sObjectName", "Id='12345'", raise_error=True
            )
