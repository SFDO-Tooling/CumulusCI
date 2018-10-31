from __future__ import unicode_literals

import mock
import os
import unittest

from cumulusci.tasks import util
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.utils import temporary_dir
from cumulusci.tests.util import DummyLogger


class TestUtilTasks(unittest.TestCase):
    def setUp(self):
        os.mkdir(os.path.join(self.tempdir, ".git"))
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.org_config = OrgConfig({}, "test")
        self.task_config = TaskConfig({})

    def run(self, result=None):
        with temporary_dir() as d:
            self.tempdir = d
            super(TestUtilTasks, self).run(result)

    @mock.patch("cumulusci.tasks.util.download_extract_zip")
    def test_DownloadZip(self, download_extract_zip):
        target = os.path.join(self.tempdir, "extracted")
        task_config = TaskConfig({"options": {"url": "http://test", "dir": target}})
        task = util.DownloadZip(self.project_config, task_config, self.org_config)
        task()
        download_extract_zip.assert_called_once_with("http://test", target, None)

    def test_ListMetadataTypes(self):
        os.mkdir(os.path.join(self.tempdir, "src"))
        package_xml_path = os.path.join(self.tempdir, "src", "package.xml")
        with open(package_xml_path, "w") as f:
            f.write(
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
</Package>"""
            )

        task = util.ListMetadataTypes(
            self.project_config, self.task_config, self.org_config
        )
        task.logger = DummyLogger()
        task()

        output = task.logger.get_output()
        self.assertIn("Metadata types found", output)
        self.assertIn("CustomObject", output)

    @mock.patch("cumulusci.tasks.util.time")
    def test_Sleep(self, time):
        task_config = TaskConfig({"options": {"seconds": "1"}})
        task = util.Sleep(self.project_config, task_config, self.org_config)
        task()
        time.sleep.assert_called_once_with(1)

    def test_Delete__single_file(self):
        file_path = os.path.join(self.tempdir, "file")
        with open(file_path, "w") as f:
            pass

        task_config = TaskConfig({"options": {"path": "file"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        self.assertFalse(os.path.exists(file_path))

    def test_Delete__glob(self):
        target = os.path.join(self.tempdir, "dir1")
        os.mkdir(target)
        file_path = os.path.join(target, "file")
        with open(file_path, "w") as f:
            pass

        task_config = TaskConfig({"options": {"path": ["*"], "chdir": target}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        self.assertFalse(os.path.exists(file_path))

    def test_Delete__subdir(self):
        target = os.path.join(self.tempdir, "dir1")
        os.mkdir(target)

        task_config = TaskConfig({"options": {"path": "dir1"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

        self.assertFalse(os.path.exists(target))

    def test_Delete__no_match(self):
        task_config = TaskConfig({"options": {"path": "bogus"}})
        task = util.Delete(self.project_config, task_config, self.org_config)
        task()

    @mock.patch("cumulusci.tasks.util.findReplace")
    def test_FindReplace(self, findReplace):
        task_config = TaskConfig({"options": {"find": "foo", "path": ".", "max": 1}})
        task = util.FindReplace(self.project_config, task_config, self.org_config)
        task()
        findReplace.assert_called_once()

    @mock.patch("cumulusci.tasks.util.findReplaceRegex")
    def test_FindReplaceRegex(self, findReplaceRegex):
        task_config = TaskConfig({"options": {"find": "foo", "path": "."}})
        task = util.FindReplaceRegex(self.project_config, task_config, self.org_config)
        task()
        findReplaceRegex.assert_called_once()

    def test_CopyFile(self):
        src = os.path.join(self.tempdir, "src")
        with open(src, "w"):
            pass
        dest = os.path.join(self.tempdir, "dest")

        task_config = TaskConfig({"options": {"src": src, "dest": dest}})
        task = util.CopyFile(self.project_config, task_config, self.org_config)
        task()

        self.assertTrue(os.path.exists(dest))

    def test_LogLine(self):
        task_config = TaskConfig({"options": {"level": "debug", "line": "test"}})
        task = util.LogLine(self.project_config, task_config, self.org_config)
        task.logger = DummyLogger()
        task()
        output = task.logger.get_output()
        self.assertEqual("Beginning task: LogLine\n\ntest", output)

    def test_PassOptionAsResult(self):
        task_config = TaskConfig({"options": {"result": "test"}})
        task = util.PassOptionAsResult(
            self.project_config, task_config, self.org_config
        )
        task()
        self.assertEqual("test", task.result)

    def test_PassOptionAsReturnValue(self):
        task_config = TaskConfig({"options": {"key": "foo", "value": "bar"}})
        task = util.PassOptionAsReturnValue(
            self.project_config, task_config, self.org_config
        )
        result = task()
        self.assertEqual("bar", result["foo"])
