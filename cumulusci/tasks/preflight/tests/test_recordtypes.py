from unittest.mock import Mock

from cumulusci.tasks.preflight.recordtypes import CheckSObjectRecordTypes
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRecordTypePreflights:
    def test_record_type_preflight(self):
        task = create_task(CheckSObjectRecordTypes, {})
        task.tooling = Mock()
        task.tooling.query_all.return_value = {
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

        task.tooling.query_all.assert_called_once_with(
            "Select SobjectType, FullName FROM RecordType"
        )
        assert task.return_values == {
            "Account": ["Business_Account", "PersonAccount"],
            "ActionPlanTemplate": ["Default"],
        }
