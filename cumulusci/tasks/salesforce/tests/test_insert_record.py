from unittest import mock, TestCase

from cumulusci.tasks.salesforce.insert_record import InsertRecord
from cumulusci.core.exceptions import TaskOptionsError
from .util import create_task


class TestCreateRecord(TestCase):
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

    def test_syntax_errors(self):
        task = create_task(
            InsertRecord,
            {
                "object": "PermissionSet",
                "values": "Name:Hard:Delete,PermissionsB:ulkApiHardDelete:true",
            },
        )
        task._init_task()
        with self.assertRaises(TaskOptionsError):
            task()
