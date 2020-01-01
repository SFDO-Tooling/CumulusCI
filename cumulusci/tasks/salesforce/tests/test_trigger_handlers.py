from unittest import mock
import responses
import unittest
from cumulusci.tasks.salesforce import SetTDTMHandlerStatus
from cumulusci.core.exceptions import TaskOptionsError, CumulusCIException
from .util import create_task


class test_trigger_handlers(unittest.TestCase):
    def test_init_options(self):
        task = create_task(
            SetTDTMHandlerStatus, {"handlers": ["TestTDTM"], "active": False}
        )

        assert task.options["handlers"] == ["TestTDTM"]

        with self.assertRaises(TaskOptionsError):
            task = create_task(
                SetTDTMHandlerStatus, {"handlers": ["TestTDTM"], "restore": True}
            )

    @responses.activate
    def test_missing_handler_object(self):
        task = create_task(
            SetTDTMHandlerStatus, {"handlers": ["TestTDTM"], "active": False}
        )
        task.api_version = "47.0"
        responses.add(
            method="GET",
            url=task.org_config.instance_url + "/services/data/v47.0/sobjects",
            json={"sobjects": [{"name": "t__c"}]},
            status=200,
        )

        with self.assertRaises(CumulusCIException):
            task()

    @responses.activate
    def test_set_status(self):
        task = create_task(
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
    def test_set_status__all_handlers(self):
        task = create_task(SetTDTMHandlerStatus, {"active": False, "namespace": "npsp"})
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
    def test_set_status_namespaced(self):
        task = create_task(
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
    def test_restore(self):
        task = create_task(
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

        m = mock.mock_open(read_data="'Test__c:TestTDTM': True")
        with mock.patch("builtins.open", m):
            with mock.patch("os.remove") as rm_patch:
                task()

                m.assert_any_call("resto.yml", "r")
                rm_patch.assert_called_once_with("resto.yml")

        assert len(responses.calls) == 3

    @responses.activate
    def test_create_restore_file(self):
        task = create_task(
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
        m = mock.mock_open()
        with mock.patch("builtins.open", m):
            with mock.patch("yaml.safe_dump") as yaml_mock:
                task()

            m.assert_any_call("resto.yml", "w")
            yaml_mock.assert_called_once_with(
                {"Test__c:TestTDTM": True, "Test__c:Test": True}, m.return_value
            )

        assert len(responses.calls) == 4
