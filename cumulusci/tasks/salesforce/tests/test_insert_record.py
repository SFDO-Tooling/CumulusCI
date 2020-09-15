from unittest import mock
import re

import pytest
import responses

from cumulusci.tasks.salesforce.insert_record import InsertRecord
from cumulusci.core.exceptions import TaskOptionsError, SalesforceException
from simple_salesforce.exceptions import SalesforceError
from .util import create_task


class TestCreateRecord:
    def test_run_task(self):
        task = create_task(
            InsertRecord,
            {
                "object": "PermissionSet",
                "values": "Name:HardDelete,PermissionsBulkApiHardDelete:true",
            },
        )
        create = mock.Mock()
        task.sf = mock.Mock(create=create)
        task.sf.PermissionSet.create.return_value = {
            "id": "0PS3D000000MKTqWAO",
            "success": True,
            "errors": [],
        }

        task._run_task()
        task.sf.PermissionSet.create.assert_called_with(
            {"Name": "HardDelete", "PermissionsBulkApiHardDelete": "true"}
        )

    def test_salesforce_error_returned_by_simple_salesforce(self):
        "Tests the just-in-case path where SimpleSalesforce does not raise an exception"
        task = create_task(
            InsertRecord,
            {
                "object": "PermissionSet",
                "values": "Name:HardDelete,PermissionsBulkApiHardDelete:true",
            },
        )
        create = mock.Mock()
        task.sf = mock.Mock(create=create)
        task.sf.PermissionSet.create.return_value = {
            "success": False,
            "errors": [
                {
                    "errorCode": "NOT_FOUND",
                    "message": "The requested resource does not exist",
                }
            ],
        }
        with pytest.raises(SalesforceException):
            task._run_task()

    @responses.activate
    def test_salesforce_error_raised_by_simple_salesforce(self):
        task = create_task(
            InsertRecord,
            {
                "object": "PermissionSet",
                "values": "Name:HardDelete,PermissionsBulkApiHardDelete:true",
            },
        )
        responses.add(
            responses.POST,
            re.compile(r"https://test.salesforce.com/services/data/v49.0/.*"),
            content_type="application/json",
            status=404,
            json={
                "success": False,
                "errors": [
                    {
                        "errorCode": "NOT_FOUND",
                        "message": "The requested resource does not exist",
                    }
                ],
            },
        )
        task._init_task()
        with pytest.raises(SalesforceError):
            task._run_task()

    def test_syntax_errors(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                InsertRecord,
                {
                    "object": "PermissionSet",
                    "values": "Name:Hard:Delete,PermissionsB:ulkApiHardDelete:true",
                },
            )
