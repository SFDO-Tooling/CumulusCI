import unittest
import shutil
import tempfile
import pytest
import os.path
import textwrap

from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.core.config import TaskConfig
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.robotframework import RobotLint
from cumulusci.core.exceptions import CumulusCIFailure


class TestRobotLint(MockLoggerMixin, unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def make_test_file(self, data, suffix=".robot", name="test"):
        filename = os.path.join(self.tmpdir, "{}{}".format(name, suffix))
        with open(filename, "w") as f:
            f.write(textwrap.dedent(data))
        return filename

    def test_exception_on_error(self):
        """Verify CumulusCIFailure is throws on rule violations"""
        path = self.make_test_file(
            """
        *** Test Cases ***
        Example
            log  hello, world
        """
        )
        task = create_task(
            RobotLint,
            {"path": path, "ignore": "all", "error": "RequireTestDocumentation"},
        )
        expected = "1 error was detected"
        with pytest.raises(CumulusCIFailure, match=expected):
            task()
        assert len(self.task_log["error"]) == 1

    def test_unicode_filenames(self):
        path = self.make_test_file(
            """
        *** Keywords ***
        Example
            # no documentation or body
        """,
            name="\u2601",
        )
        task = create_task(
            RobotLint,
            {"path": path, "ignore": "all", "error": "RequireKeywordDocumentation"},
        )
        assert len(self.task_log["error"]) == 0
        expected = "1 error was detected"

        with pytest.raises(CumulusCIFailure, match=expected):
            task()
        print("after calling task")

    def test_ignore_all(self):
        path = self.make_test_file(
            """
        *** Keywords ***
        Duplicate keyword name
            # no documentation or body
        Duplicate keyword name
            # no documentation or body
        *** Test Cases ***
        Duplicate testcase name
            # no documentation or body
        Duplicate testcase name
        """
        )
        task = create_task(RobotLint, {"path": path, "ignore": "all"})
        task()
        assert len(self.task_log["warning"]) == 0
        assert len(self.task_log["error"]) == 0
        assert len(self.task_log["critical"]) == 0
        assert len(self.task_log["debug"]) == 0
