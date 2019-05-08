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
        task._init_task()
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query_all.return_value = {
            "totalSize": 1,
            "records": [
                {
                    "MemberType": "CustomObject",
                    "MemberName": "Test__c",
                    "RevisionNum": 1,
                }
            ],
        }
        task._run_task()
        self.assertIn("CustomObject: Test__c", task.logger.info.call_args[0][0])

    def test_run_task__no_changes(self):
        task = create_task(ListChanges)
        task._init_task()
        task.tooling = mock.Mock()
        task.logger = mock.Mock()
        task.tooling.query_all.return_value = {"totalSize": 0, "records": []}
        task._run_task()
        self.assertIn("Found no changes.", task.logger.info.call_args[0][0])

    def test_run_task__snapshot(self):
        with temporary_dir():
            task = create_task(ListChanges, {"snapshot": True})
            task._init_task()
            task.tooling = mock.Mock()
            messages = []
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionNum": 1,
                    }
                ],
            }
            task._run_task()
            self.assertTrue(
                os.path.exists(os.path.join(".cci", "snapshot", "test.json"))
            )
            self.assertIn("CustomObject: Test__c", messages)

            task = create_task(ListChanges)
            task._init_task()
            task.tooling = mock.Mock()
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionNum": 1,
                    }
                ],
            }
            task._run_task()
            self.assertIn("Ignored 1 changed components in the scratch org.", messages)

    def test_filter_changes__include(self):
        foo = {"MemberType": "CustomObject", "MemberName": "foo__c", "RevisionNum": 1}
        bar = {"MemberType": "CustomObject", "MemberName": "bar__c", "RevisionNum": 1}
        foobar = {
            "MemberType": "CustomObject",
            "MemberName": "foobar__c",
            "RevisionNum": 1,
        }
        task = create_task(ListChanges, {"include": "foo", "exclude": "bar"})
        filtered = task._filter_changes({"records": [foo, bar, foobar]})
        self.assertEqual([foo], filtered)


class TestRetrieveChanges(unittest.TestCase):
    """Retrieve changed components from a scratch org"""

    def test_run_task(self):
        with temporary_dir() as path:
            task = create_task(RetrieveChanges, {"path": path, "include": "Test"})
            task._init_task()
            task.tooling = mock.Mock()
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Test__c",
                        "RevisionNum": 1,
                    }
                ],
            }
            zf = zipfile.ZipFile(io.BytesIO(), "w")
            zf.writestr("objects/Test__c.object", "<root />")
            task.api_class = mock.Mock(return_value=mock.Mock(return_value=zf))
            task._run_task()
            with open(os.path.join(path, "package.xml"), "r") as f:
                package_xml = f.read()
        self.assertIn("<members>Test__c</members>", package_xml)

    def test_run_task__merge_changes(self):
        # If there is already an existing package,
        # we should add to it rather than overwriting it.
        with temporary_dir() as path:
            with open("package.xml", "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Object1</members>
        <name>CustomObject</name>
    </types>
</Package>
"""
                )
            task = create_task(RetrieveChanges, {"path": path})
            task._init_task()
            task.tooling = mock.Mock()
            task.tooling.query_all.return_value = {
                "totalSize": 1,
                "records": [
                    {
                        "MemberType": "CustomObject",
                        "MemberName": "Object2",
                        "RevisionNum": 1,
                    }
                ],
            }
            task.api_class = mock.Mock()
            task._run_task()

            package_xml = task.api_class.call_args[0][1]
            self.maxDiff = None
            self.assertEqual(
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Object1</members>
        <members>Object2</members>
        <name>CustomObject</name>
    </types>
    <version>45.0</version>
</Package>""",
                package_xml,
            )

    def test_run_task__no_changes(self):
        with temporary_dir() as path:
            task = create_task(RetrieveChanges, {"path": path})
            task._init_task()
            messages = []
            task.tooling = mock.Mock()
            task.tooling.query_all.return_value = {"totalSize": 0, "records": []}
            task.logger = mock.Mock()
            task.logger.info = messages.append
            task._run_task()
            self.assertIn("No changes to retrieve", messages)
