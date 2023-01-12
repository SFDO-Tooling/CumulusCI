import json
from unittest.mock import patch

import pytest
import responses

from cumulusci.core.exceptions import SalesforceException
from cumulusci.tasks.salesforce.composite import API_ROLLBACK_MESSAGE, CompositeApi
from cumulusci.tests.util import CURRENT_SF_API_VERSION

from .util import create_task

COMPOSITE_REQUEST = {
    "allOrNone": True,
    "compositeRequest": [
        {
            "method": "GET",
            "url": f"/services/data/v{CURRENT_SF_API_VERSION}/query/?q=SELECT+Id+FROM+RecordType+WHERE+SobjectType+=+'Account' AND DeveloperName = 'Educational_Institution'",
            "referenceId": "schoolRt",
        },
        {
            "method": "POST",
            "url": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Account",
            "referenceId": "uni",
            "body": {
                "Name": "Connected Campus University",
                "RecordTypeId": "@{schoolRt.records[0].Id}",
            },
        },
        {
            "method": "POST",
            "url": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/User",
            "referenceId": "sophiaUser",
            "body": {
                "FirstName": "Sophia",
                "LastName": "Student",
                "Alias": "sophia",
                "City": "San Francisco",
                "Country": "USA",
                "Email": "sofia@connected.edu",
                "EmailEncodingKey": "utf-8",
                "LanguageLocaleKey": "en_US",
                "LocaleSidKey": "en_US",
                "MobilePhone": "(650) 555-1212",
                "Phone": "(650) 555-1212",
                "PostalCode": "94105",
                "ProfileId": "@{profiles.records[0].Id}",
                "State": "CA",
                "Street": "1 Market Street",
                "TimeZoneSidKey": "America/Los_Angeles",
                "Username": "sofia@connected.edu",
            },
        },
    ],
}
COMPOSITE_RESPONSE = {
    "compositeResponse": [
        {
            "body": {
                "totalSize": 1,
                "done": True,
                "records": [
                    {
                        "attributes": {
                            "type": "RecordType",
                            "url": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/RecordType/01211000002FEJ0AAO",
                        },
                        "Id": "01211000002FEJ0AAO",
                    }
                ],
            },
            "httpHeaders": {},
            "httpStatusCode": 200,
            "referenceId": "schoolRt",
        },
        {
            "body": {"id": "00111000021SzRwAAK", "success": True, "errors": []},
            "httpHeaders": {
                "Location": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/Account/00111000021SzRwAAK"
            },
            "httpStatusCode": 201,
            "referenceId": "uni",
        },
        {
            "body": {"id": "00511000009y7uaAAA", "success": True, "errors": []},
            "httpHeaders": {
                "Location": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/User/00511000009y7uaAAA"
            },
            "httpStatusCode": 201,
            "referenceId": "sophiaUser",
        },
    ]
}


class TestCompositeApi:
    @responses.activate
    @patch("cumulusci.tasks.salesforce.composite.CliTable")
    def test_composite_request(self, table, tmp_path):
        test_json = tmp_path / "test.json"
        test_json.write_text(json.dumps(COMPOSITE_REQUEST))
        task = create_task(
            CompositeApi,
            {
                "data_files": [
                    str(test_json),
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite",
            status=200,
            json=COMPOSITE_RESPONSE,
        )

        task()

        assert len(responses.calls) == 1
        request_body = json.loads(responses.calls[0].request.body)
        assert request_body == COMPOSITE_REQUEST

    @responses.activate
    @patch("cumulusci.tasks.salesforce.composite.CliTable")
    def test_composite_request_success_message(self, table, tmp_path):
        test_json = tmp_path / "test.json"
        test_json.write_text(json.dumps(COMPOSITE_REQUEST))
        task = create_task(
            CompositeApi,
            {
                "data_files": [
                    str(test_json),
                ],
            },
        )
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite",
            status=200,
            json=COMPOSITE_RESPONSE,
        )
        expected_table_data = [
            ["ReferenceId", "Success"],
            ["schoolRt", True],
            ["uni", True],
            ["sophiaUser", True],
        ]

        task()
        table.assert_called_once_with((expected_table_data), title="Subrequest Results")

    @responses.activate
    @patch("cumulusci.tasks.salesforce.composite.CliTable")
    def test_composite_request_exception(self, table, tmp_path):
        test_json = tmp_path / "test.json"
        test_json.write_text(json.dumps(COMPOSITE_REQUEST))
        task = create_task(
            CompositeApi,
            {
                "data_files": [
                    str(test_json),
                ],
            },
        )

        error_response = {
            "compositeResponse": [
                {
                    "body": [
                        {
                            "errorCode": "PROCESSING_HALTED",
                            "message": "Invalid reference specified. No value for schoolRt.records[0].Id found in schoolRt",
                        }
                    ],
                    "httpHeaders": {},
                    "httpStatusCode": 400,
                    "referenceId": "badref",
                },
                {
                    "body": [
                        {
                            "errorCode": "PROCESSING_HALTED",
                            "message": API_ROLLBACK_MESSAGE,
                        }
                    ],
                    "httpHeaders": {},
                    "httpStatusCode": 400,
                    "referenceId": "rollback",
                },
            ]
        }
        responses.add(
            method="POST",
            url=f"{task.org_config.instance_url}/services/data/v{CURRENT_SF_API_VERSION}/composite",
            status=200,
            json=error_response,
        )
        expected_table_data = [
            ["ReferenceId", "Message"],
            [
                "badref",
                "Invalid reference specified. No value for schoolRt.records[0].Id found in schoolRt",
            ],
        ]

        with pytest.raises(SalesforceException):
            task()

        table.assert_called_once_with(
            (expected_table_data),
        )

    def test_json_processing(self):
        request = COMPOSITE_REQUEST["compositeRequest"].copy()
        request.append(
            {
                "method": "PATCH",
                "url": f"/services/data/v{CURRENT_SF_API_VERSION}/sobjects/User",
                "body": {
                    "Id": "%%%USERID%%%",
                    "Email": "test@testerino.patch",
                    "Test__c": "%%%NAMESPACE%%%Foo__c",
                },
            }
        )
        body = json.dumps(request)
        task = create_task(
            CompositeApi,
            {
                "data_files": [
                    "dummy_path",
                ],
                "randomize_username": True,
                "managed": True,
            },
        )

        task.project_config.project__package__namespace = "NS"
        processed_body = task._process_json(body)
        assert "USER_ID" in processed_body
        assert "NS__Foo__c" in processed_body

        assert '"Username": "sofia@connected.' in processed_body
        assert '"Username": "sofia@connected.edu"' not in processed_body
