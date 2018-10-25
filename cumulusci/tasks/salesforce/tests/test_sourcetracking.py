import io
import mock
import os
import unittest
import zipfile

from cumulusci.tasks.salesforce.sourcetracking import ListChanges
from cumulusci.tasks.salesforce.sourcetracking import RetrieveChanges
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils import temporary_dir


class TestListChanges(unittest.TestCase):
    """List the changes from a scratch org"""

    def test_run_task(self):
        task = create_task(ListChanges)
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query.return_value = {
            "totalSize": 1,
            "records": [{"MemberType": "CustomObject", "MemberName": "Test__c"}],
        }
        task()
        self.assertIn("CustomObject: Test__c", task.logger.info.call_args[0][0])

    def test_run_task__no_changes(self):
        task = create_task(ListChanges)
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query.return_value = {"totalSize": 0, "records": []}
        task()
        self.assertIn("Found no changes.", task.logger.info.call_args[0][0])


class TestRetrieveChanges(unittest.TestCase):
    """Retrieve changed components from a scratch org"""

    def test_run_task(self):
        with temporary_dir() as path:
            task = create_task(RetrieveChanges, {"path": path, "include": "Test"})
            task.tooling = mock.Mock()
            task.tooling.query.return_value = {
                "totalSize": 1,
                "records": [{"MemberType": "CustomObject", "MemberName": "Test__c"}],
            }
            zf = zipfile.ZipFile(io.BytesIO(), "w")
            zf.writestr("objects/Test__c.object", "<root />")
            task.api_class = mock.Mock(return_value=mock.Mock(return_value=zf))
            task()
            with open(os.path.join(path, "package.xml"), "r") as f:
                package_xml = f.read()
        self.assertIn("<members>Test__c</members>", package_xml)
