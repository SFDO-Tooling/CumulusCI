import datetime
import json
import os
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce import DescribeMetadataTypes
from cumulusci.tasks.salesforce.nonsourcetracking import (
    ListComponents,
    ListNonSourceTrackable,
    RetrieveComponents,
)
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir


class TestListNonSourceTrackable:
    @pytest.mark.parametrize(
        "json_data, expected_status,error_msg",
        [
            (None, 404, "Failed to retrieve response with status code 404"),
            (
                {"types": {"Scontrol": {"channels": {}}}},
                200,
                "Api version 44.0 not supported",
            ),
        ],
    )
    @responses.activate
    def test_run_get_types_details(
        self, create_task_fixture, json_data, expected_status, error_msg
    ):
        options = {"api_version": 44.0}
        responses.add(
            "GET",
            f"https://dx-extended-coverage.my.salesforce-sites.com/services/apexrest/report?version={options['api_version']}",
            json=json_data,
            status=expected_status,
        )
        task = create_task_fixture(ListNonSourceTrackable, options)
        task._init_task()
        with pytest.raises(CumulusCIException, match=error_msg):
            task._run_task()

    @responses.activate
    def test_run_task_list_metadatatypes(self, create_task_fixture):
        options = {"api_version": 44.0}
        return_value = {
            "types": {
                "Scontrol": {
                    "channels": {"sourceTracking": False, "metadataApi": True}
                },
                "SharingRules": {
                    "channels": {"sourceTracking": False, "metadataApi": True}
                },
                "ApexClass": {
                    "channels": {"sourceTracking": True, "metadataApi": True}
                },
                "CustomObject": {
                    "channels": {"sourceTracking": True, "metadataApi": True}
                },
                "MessagingChannel": {
                    "channels": {"sourceTracking": True, "metadataApi": True}
                },
            }
        }
        responses.add(
            "GET",
            f"https://dx-extended-coverage.my.salesforce-sites.com/services/apexrest/report?version={options['api_version']}",
            json=return_value,
            status=200,
        )

        task = create_task_fixture(ListNonSourceTrackable, options)
        task._init_task()
        with mock.patch.object(
            DescribeMetadataTypes,
            "_run_task",
            return_value=["Scontrol", "ApexClass", "CustomObject", "SharingRules"],
        ):
            non_source_trackable = task._run_task()
            assert non_source_trackable == ["Scontrol", "SharingRules"]


class TestListComponents:
    def test_init_task(self, create_task_fixture):
        with mock.patch.object(
            ListNonSourceTrackable,
            "_run_task",
            return_value=["SharingRules", "Scontrol"],
        ):
            task = create_task_fixture(ListComponents, {})
            task._init_task()
            assert task.options["metadata_types"] == ["SharingRules", "Scontrol"]

    def test_check_api_result(self, create_task_fixture):
        options = {"metadata_types": "SharingRules"}
        task = create_task_fixture(ListComponents, options)
        expected = [
            {
                "MemberType": "SharingRules",
                "MemberName": "Order",
                "lastModifiedByName": "Automated process",
                "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
            },
            {
                "MemberType": "SharingRules",
                "MemberName": "BusinessBrand",
                "lastModifiedByName": "User User",
                "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
            },
        ]
        result = mock.Mock(
            return_value={
                "SharingRules": [
                    {
                        "createdById": "0055j000008HpiJAAS",
                        "createdByName": "Alpha",
                        "createdDate": datetime.datetime(1970, 1, 1, 0, 0),
                        "fileName": "sharingRules/Order.sharingRules",
                        "fullName": "Order",
                        "id": None,
                        "lastModifiedById": "0055j000008HpiJAAS",
                        "lastModifiedByName": "Automated process",
                        "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
                        "manageableState": None,
                        "namespacePrefix": None,
                        "type": "SharingRules",
                    },
                    {
                        "createdById": "0055j000008HpiJAAS",
                        "createdByName": "Beta",
                        "createdDate": datetime.datetime(1970, 1, 1, 0, 0),
                        "fileName": "sharingRules/BusinessBrand.sharingRules",
                        "fullName": "BusinessBrand",
                        "id": None,
                        "lastModifiedById": "0055j000008HpiJAAS",
                        "lastModifiedByName": "User User",
                        "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
                        "manageableState": None,
                        "namespacePrefix": None,
                        "type": "SharingRules",
                    },
                ]
            }
        )
        messages = []
        task._init_task()
        task.logger = mock.Mock()
        task.logger.info = messages.append
        task.api_class = mock.Mock(return_value=result)
        components = task._run_task()
        assert components == expected
        assert (
            "Found 2 non source trackable components in the org for the given types."
            in messages
        )


@mock.patch("cumulusci.tasks.salesforce.sourcetracking.sfdx")
class TestRetrieveComponents:
    def test_init_options__sfdx_format(self, sfdx, create_task_fixture):
        with temporary_dir():
            project_config = create_project_config()
            project_config.project__source_format = "sfdx"
            with open("sfdx-project.json", "w") as f:
                json.dump(
                    {"packageDirectories": [{"path": "force-app", "default": True}]}, f
                )
            task = create_task_fixture(
                RetrieveComponents, {"metadata_types": "SharingRules"}, project_config
            )
            assert not task.md_format
            assert task.options["path"] == "force-app"

    def test_run_task(self, sfdx, create_task_fixture):
        sfdx_calls = []
        sfdx.side_effect = lambda cmd, *args, **kw: sfdx_calls.append(cmd)

        with temporary_dir():
            task = create_task_fixture(
                RetrieveComponents,
                {
                    "include": "alpha",
                    "namespace_tokenize": "ns",
                    "metadata_types": "SharingRules",
                },
            )
            task._init_task()
            messages = []
            with mock.patch.object(
                ListComponents,
                "_get_components",
                return_value=[
                    {
                        "MemberType": "SharingRules",
                        "MemberName": "alpha",
                        "lastModifiedByName": "Automated process",
                        "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
                    },
                    {
                        "MemberType": "SharingRules",
                        "MemberName": "BusinessBrand",
                        "lastModifiedByName": "User User",
                        "lastModifiedDate": datetime.datetime(1970, 1, 1, 0, 0),
                    },
                ],
            ):
                task.logger = mock.Mock()
                task.logger.info = messages.append
                task._run_task()
                assert "SharingRules: alpha" in messages
                assert "SharingRules: BusinessBrand" not in messages
                assert sfdx_calls == [
                    "project convert mdapi",
                    "project retrieve start",
                    "project convert source",
                ]
                assert os.path.exists(os.path.join("src", "package.xml"))

    def test_run_task__no_changes(self, sfdx, create_task_fixture):
        with temporary_dir() as path:
            task = create_task_fixture(
                RetrieveComponents, {"path": path, "metadata_types": "SharingRules"}
            )
            task._init_task()
            messages = []
            with mock.patch.object(ListComponents, "_get_components", return_value=[]):
                task.logger = mock.Mock()
                task.logger.info = messages.append
                task._run_task()
                assert "No components to retrieve" in messages
