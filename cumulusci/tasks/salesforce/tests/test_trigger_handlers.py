from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.tasks.salesforce import SetTDTMHandlerStatus


class TestTriggerHandlers:
    def test_init_options(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus, {"handlers": ["TestTDTM"], "active": False}
        )

        assert task.options["handlers"] == ["TestTDTM"]

        with pytest.raises(TaskOptionsError):
            task = create_task_fixture(
                SetTDTMHandlerStatus,
                {"handlers": ["TestTDTM"], "restore": True, "restore_file": False},
            )

        with pytest.raises(TaskOptionsError):
            task = create_task_fixture(
                SetTDTMHandlerStatus,
                {"handlers": ["TestTDTM"], "restore": True, "restore_file": "False"},
            )

    @responses.activate
    def test_missing_handler_object(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus, {"handlers": ["TestTDTM"], "active": False}
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "t__c"}]},
            status=200,
        )

        with pytest.raises(CumulusCIException):
            task()

    @responses.activate
    def test_set_status(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus,
            {"handlers": ["TestTDTM"], "active": False, "namespace": "npsp"},
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "Trigger_Handler__c"}]},
            status=200,
        )
        responses.add(
            method="GET",
            url=task.org_config.instance_url
            + "/services/data/v47.0/query/?q=SELECT+Id%2C+Class__c%2C+Object__c%2C+Active__c+FROM+Trigger_Handler__c",
            status=200,
            json={
                "records": [
                    {
                        "Id": "000000000000000",
                        "Class__c": "TestTDTM",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                    {
                        "Id": "000000000000001",
                        "Class__c": "Test",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                ]
            },
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/Trigger_Handler__c/000000000000000",
            status=204,
            json={"Active__c": False},
        )
        task()

        assert len(responses.calls) == 3

    @responses.activate
    def test_set_status__all_handlers(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus, {"active": False, "namespace": "npsp"}
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "Trigger_Handler__c"}]},
            status=200,
        )
        responses.add(
            method="GET",
            url=task.org_config.instance_url
            + "/services/data/v47.0/query/?q=SELECT+Id%2C+Class__c%2C+Object__c%2C+Active__c+FROM+Trigger_Handler__c",
            status=200,
            json={
                "records": [
                    {
                        "Id": "000000000000000",
                        "Class__c": "TestTDTM",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                    {
                        "Id": "000000000000001",
                        "Class__c": "Test",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                ]
            },
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/Trigger_Handler__c/000000000000000",
            status=204,
            json={"Active__c": False},
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/Trigger_Handler__c/000000000000001",
            status=204,
            json={"Active__c": False},
        )
        task()

        assert len(responses.calls) == 4

    @responses.activate
    def test_set_status_namespaced(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus,
            {"handlers": ["Test__c:TestTDTM"], "active": False, "namespace": "npsp"},
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "npsp__Trigger_Handler__c"}]},
            status=200,
        )
        responses.add(
            method="GET",
            url=task.org_config.instance_url
            + "/services/data/v47.0/query/?q=SELECT+Id%2C+npsp__Class__c%2C+npsp__Object__c%2C+npsp__Active__c+FROM+npsp__Trigger_Handler__c",
            status=200,
            json={
                "records": [
                    {
                        "Id": "000000000000000",
                        "npsp__Class__c": "TestTDTM",
                        "npsp__Object__c": "Test__c",
                        "npsp__Active__c": True,
                    },
                    {
                        "Id": "000000000000001",
                        "npsp__Class__c": "Test",
                        "npsp__Object__c": "Test__c",
                        "npsp__Active__c": True,
                    },
                ]
            },
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/npsp__Trigger_Handler__c/000000000000000",
            status=204,
            json={"npsp__Active__c": False},
        )
        task()

        assert len(responses.calls) == 3

    @responses.activate
    def test_restore(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus,
            {"restore": True, "restore_file": "resto.yml", "namespace": "npsp"},
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "npsp__Trigger_Handler__c"}]},
            status=200,
        )
        responses.add(
            method="GET",
            url=task.org_config.instance_url
            + "/services/data/v47.0/query/?q=SELECT+Id%2C+npsp__Class__c%2C+npsp__Object__c%2C+npsp__Active__c+FROM+npsp__Trigger_Handler__c",
            status=200,
            json={
                "records": [
                    {
                        "Id": "000000000000000",
                        "npsp__Class__c": "TestTDTM",
                        "npsp__Object__c": "Test__c",
                        "npsp__Active__c": False,
                    },
                    {
                        "Id": "000000000000001",
                        "npsp__Class__c": "Test",
                        "npsp__Object__c": "Test__c",
                        "npsp__Active__c": False,
                    },
                ]
            },
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/npsp__Trigger_Handler__c/000000000000000",
            status=204,
            json={"npsp__Active__c": True},
        )

        op = mock.mock_open(read_data="'Test__c:TestTDTM': True")
        with mock.patch("cumulusci.utils.fileutils.FSResource.open", op):
            with mock.patch("cumulusci.utils.fileutils.FSResource.unlink") as unlink:
                task()

                op.assert_any_call("r")
                unlink.assert_called_once()

        assert len(responses.calls) == 3

    @responses.activate
    def test_create_restore_file(self, create_task_fixture):
        task = create_task_fixture(
            SetTDTMHandlerStatus,
            {
                "handlers": ["Test__c"],
                "active": False,
                "restore_file": "resto.yml",
                "namespace": "npsp",
            },
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "Trigger_Handler__c"}]},
            status=200,
        )
        responses.add(
            method="GET",
            url=task.org_config.instance_url
            + "/services/data/v47.0/query/?q=SELECT+Id%2C+Class__c%2C+Object__c%2C+Active__c+FROM+Trigger_Handler__c",
            status=200,
            json={
                "records": [
                    {
                        "Id": "000000000000000",
                        "Class__c": "TestTDTM",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                    {
                        "Id": "000000000000001",
                        "Class__c": "Test",
                        "Object__c": "Test__c",
                        "Active__c": True,
                    },
                ]
            },
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/Trigger_Handler__c/000000000000000",
            status=204,
            json={"Active__c": False},
        )
        responses.add(
            method="PATCH",
            url=task.org_config.instance_url
            + "/services/data/v47.0/sobjects/Trigger_Handler__c/000000000000001",
            status=204,
            json={"Active__c": False},
        )
        op = mock.mock_open()
        with mock.patch("cumulusci.utils.fileutils.FSResource.open", op):
            with mock.patch("yaml.safe_dump") as yaml_mock:
                task()

            op.assert_any_call("w")
            yaml_mock.assert_called_once_with(
                {"Test__c:TestTDTM": True, "Test__c:Test": True}, op.return_value
            )

        assert len(responses.calls) == 4
