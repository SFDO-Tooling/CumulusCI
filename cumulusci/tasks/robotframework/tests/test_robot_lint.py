import unittest
import shutil
import tempfile
import pytest
import os.path
import textwrap

from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tests.util import create_project_config
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

    def make_test_file(self, data, suffix=".robot", name="test", dir=None):
        """Create a temporary test file"""
        dir = self.tmpdir if dir is None else dir
        filename = os.path.join(dir, "{}{}".format(name, suffix))
        with open(filename, "w") as f:
            f.write(textwrap.dedent(data))
        return filename

    def test_no_duplicate_files(self):
        """Verify that the working set of files has no duplicates"""
        path = self.make_test_file(
            """
            *** Test Cases ***
            Example
                log  hello, world
            """,
            suffix=".robot",
        )
        glob_path = "{}/*.robot".format(self.tmpdir)

        task = create_task(
            RobotLint,
            {
                "path": [glob_path, path],
                "ignore": "all",
                "error": "RequireTestDocumentation",
            },
        )
        expected = "1 error was detected"
        with pytest.raises(CumulusCIFailure, match=expected):
            task()

    def test_exception_on_error(self):
        """Verify CumulusCIFailure is thrown on rule violations"""
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
        assert self.task_log["error"] == [
            "E: 4, 0: No testcase documentation (RequireTestDocumentation)"
        ]

    def test_unicode_filenames(self):
        """Verify this task works with files that have unicode characters in the filename"""
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

    def test_configure_option(self):
        """Verify that rule configuration options are passed to rflint"""
        task = create_task(
            RobotLint,
            {"path": self.tmpdir, "configure": "LineTooLong:40,FileTooLong:123"},
        )
        expected = ["--configure", "LineTooLong:40", "--configure", "FileTooLong:123"]
        self.assertEqual(task._get_args(), expected)

    def test_error_option(self):
        """Verify that error option is propertly translated to rflint options"""
        task = create_task(
            RobotLint, {"path": self.tmpdir, "error": "LineTooLong,FileTooLong"}
        )
        expected = ["--error", "LineTooLong", "--error", "FileTooLong"]
        self.assertEqual(task._get_args(), expected)

    def test_ignore_option(self):
        """Verify that ignore option is propertly translated to rflint options"""
        task = create_task(
            RobotLint,
            {"path": self.tmpdir, "ignore": "TooFewKeywordSteps,TooFewTestSteps"},
        )
        expected = ["--ignore", "TooFewKeywordSteps", "--ignore", "TooFewTestSteps"]
        self.assertEqual(task._get_args(), expected)

    def test_warning_option(self):
        """Verify that warning option is propertly translated to rflint options"""
        task = create_task(
            RobotLint,
            {"path": self.tmpdir, "warning": "TrailingBlankLines, TrailingWhitespace"},
        )
        expected = [
            "--warning",
            "TrailingBlankLines",
            "--warning",
            "TrailingWhitespace",
        ]
        self.assertEqual(task._get_args(), expected)

    def test_ignore_all(self):
        """Verify that -o ignore all works as expected

        We already have a test that verifies that the ignore options
        are properly translated to rflint arguments. This is more of a sanity
        check that it actually has the desired effect when the task is run.
        """
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

    def test_default_path(self):
        """Verify that if no path is provided, we search robot/<project>"""

        project_config = create_project_config()
        project_config.config["project"]["name"] = "TestPackage"
        task = create_task(RobotLint, {}, project_config=project_config)
        assert task.options["path"] == ["robot/TestPackage"]

    def test_explicit_path(self):
        """Verify an explicit path is used when given

        This also verifies that the path is converted to a proper list
        if it is a comma-separated string.
        """
        task = create_task(RobotLint, {"path": "/tmp/tests,/tmp/resources"})
        assert task.options["path"] == ["/tmp/tests", "/tmp/resources"]

    def test_wildcards(self):
        """Verify that wildcards in the path are expanded"""
        file1 = self.make_test_file("", name="a", suffix=".resource")
        file2 = self.make_test_file("", name="b", suffix=".robot")
        file3 = self.make_test_file("", name="c", suffix=".robot")

        # path with one wildcard should find one file
        task = create_task(RobotLint, {"path": "{}/*.resource".format(self.tmpdir)})
        files = sorted(task._get_files())
        self.assertEqual(files, [file1])

        # two paths with wildcards should find all three files
        task = create_task(
            RobotLint,
            {"path": "{dir}/*.resource, {dir}/*.robot".format(dir=self.tmpdir)},
        )
        files = sorted(task._get_files())
        self.assertEqual(files, [file1, file2, file3])

    def test_folder_for_path(self):
        """Verify that if the path is a folder, we process all files in the folder"""
        file1 = self.make_test_file("", name="a", suffix=".resource")
        file2 = self.make_test_file("", name="b", suffix=".robot")
        file3 = self.make_test_file("", name="c", suffix=".robot")

        task = create_task(RobotLint, {"path": self.tmpdir})
        files = sorted(task._get_files())
        self.assertEqual(files, [file1, file2, file3])

    def test_recursive_folder(self):
        """Verify that subdirectories are included when finding files"""
        subdir = tempfile.mkdtemp(dir=self.tmpdir)
        file1 = self.make_test_file("", dir=subdir)

        task = create_task(RobotLint, {"path": self.tmpdir})
        files = sorted(task._get_files())
        self.assertEqual(files, [file1])
