import io
import json
import os
from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import CumulusCIException, SfdxOrgException
from cumulusci.tasks.salesforce import DescribeMetadataTypes
from cumulusci.tasks.salesforce.nonsourcetracking import (
    ListComponents,
    ListMetadatatypes,
    RetrieveComponents,
)
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir


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


@mock.patch("sarge.Command")
class TestListComponents:
    @pytest.mark.parametrize(
        "return_code, result",
        [
            (
                0,
                b"""{
  "status": 0,
  "result": [],
  "warnings": [
    "No metadata found for type: SharingRules"
  ]
}""",
            ),
            (1, b""),
        ],
    )
    def test_check_sfdx_output(self, cmd, create_task_fixture, return_code, result):
        options = {"api_version": 44.0, "exclude": "Ignore"}
        task = create_task_fixture(ListComponents, options)
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=return_code
        )
        task._init_task()
        with mock.patch.object(
            ListMetadatatypes, "_run_task", return_value=["SharingRules"]
        ):
            if return_code:
                with pytest.raises(SfdxOrgException):
                    task._run_task()
            else:
                assert task._run_task() == []

    @pytest.mark.parametrize("options", [{"include": "alpha"}, {"exclude": "beta"}])
    def test_check_sfdx_result(self, cmd, create_task_fixture, options):
        task = create_task_fixture(ListComponents, options)
        result = b"""{
  "status": 0,
  "result": [
    {
      "createdById": "0051y00000OdeZBAAZ",
      "createdByName": "User User",
      "createdDate": "2024-01-02T06:50:03.000Z",
      "fileName": "flowDefinitions/alpha.flowDefinition",
      "fullName": "alpha",
      "id": "3001y000000ERX6AAO",
      "lastModifiedById": "0051y00000OdeZBAAZ",
      "lastModifiedByName": "User User",
      "lastModifiedDate": "2024-01-02T06:50:07.000Z",
      "manageableState": "unmanaged",
      "namespacePrefix": "myalpha",
      "type": "FlowDefinition"
    },{
      "createdById": "0051y00000OdeZBAAZ",
      "createdByName": "User User",
      "createdDate": "2024-01-02T06:50:03.000Z",
      "fileName": "flowDefinitions/beta.flowDefinition",
      "fullName": "beta",
      "id": "3001y000000ERX6AAO",
      "lastModifiedById": "0051y00000OdeZBAAZ",
      "lastModifiedByName": "User User",
      "lastModifiedDate": "2024-01-02T06:50:07.000Z",
      "manageableState": "unmanaged",
      "namespacePrefix": "myalpha",
      "type": "FlowDefinition"
    }
  ],
  "warnings": []
}"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )
        messages = []
        task._init_task()
        with mock.patch.object(
            ListMetadatatypes, "_run_task", return_value=["FlowDefinition"]
        ):
            task.logger = mock.Mock()
            task.logger.info = messages.append
            components = task._run_task()
            assert components == [
                {"MemberType": "FlowDefinition", "MemberName": "alpha"}
            ]
            assert "Found 2 non source trackable components in the org." in messages
            assert "1 remaining components after filtering." in messages


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
            task = create_task_fixture(RetrieveComponents, {}, project_config)
            assert not task.md_format
            assert task.options["path"] == "force-app"

    def test_run_task(self, sfdx, create_task_fixture):
        sfdx_calls = []
        sfdx.side_effect = lambda cmd, *args, **kw: sfdx_calls.append(cmd)

        with temporary_dir():
            task = create_task_fixture(
                RetrieveComponents, {"include": "alpha", "namespace_tokenize": "ns"}
            )
            task._init_task()
            with mock.patch.object(
                ListComponents,
                "_get_components",
                return_value=[
                    {"MemberType": "FlowDefinition", "MemberName": "alpha"},
                    {"MemberType": "FlowDefinition", "MemberName": "beta"},
                ],
            ):
                task._run_task()

                assert sfdx_calls == [
                    "force:mdapi:convert",
                    "force:source:retrieve",
                    "force:source:convert",
                ]
                assert os.path.exists(os.path.join("src", "package.xml"))

    def test_run_task__no_changes(self, sfdx, create_task_fixture):
        with temporary_dir() as path:
            task = create_task_fixture(RetrieveComponents, {"path": path})
            task._init_task()
            messages = []
            with mock.patch.object(ListComponents, "_get_components", return_value=[]):
                task.logger = mock.Mock()
                task.logger.info = messages.append
                task._run_task()
                assert "No changes to retrieve" in messages
