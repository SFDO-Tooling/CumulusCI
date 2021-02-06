from unittest.mock import Mock
import unittest

from cumulusci.tasks.preflight.recordtypes import CheckSObjectRecordTypes
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRecordTypePreflights(unittest.TestCase):
    def test_recordType_preflight(self):
        task = create_task(CheckSObjectRecordTypes, {})
        task.tooling = Mock()
        task.tooling.query.return_value = {
            "totalSize": 3,
            "records": [
                {"SobjectType": "Account", "FullName": "Account.Business_Account"},
                {"SobjectType": "Account", "FullName": "PersonAccount.PersonAccount"},
                {
                    "SobjectType": "ActionPlanTemplate",
                    "FullName": "ActionPlanTemplate.Default",
                },
            ],
        }
        task._run_task()

        task.tooling.query.assert_called_once_with(
            "Select SObjectType,FullName FROM RecordType"
        )
        assert task.return_values == {
            "Account": ["Business_Account", "PersonAccount"],
            "ActionPlanTemplate": ["Default"],
        }
