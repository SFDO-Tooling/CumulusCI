from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import CumulusCIException, SfdxOrgException
from cumulusci.tasks.salesforce import DescribeMetadataTypes
from cumulusci.tasks.salesforce.nonsourcetracking import (
    ListComponents,
    ListMetadatatypes,
)


class TestListMetadatatypes:
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
        task = create_task_fixture(ListMetadatatypes, options)
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

        task = create_task_fixture(ListMetadatatypes, options)
        task._init_task()
        with mock.patch.object(
            DescribeMetadataTypes,
            "_run_task",
            return_value=["Scontrol", "ApexClass", "CustomObject", "SharingRules"],
        ):
            non_source_trackable = task._run_task()
            assert non_source_trackable == ["Scontrol", "SharingRules"]


class TestListComponents:
    def test_run_task(self, create_task_fixture):
        options = {"api_version": 44.0, "exclude": "Ignore"}
        task = create_task_fixture(ListComponents, options)
        task._init_task()
        with mock.patch.object(
            ListMetadatatypes, "_run_task", return_value=["Scontrol", "SharingRules"]
        ):
            with pytest.raises(SfdxOrgException):
                task._run_task()
