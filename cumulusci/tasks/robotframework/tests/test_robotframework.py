from unittest import mock
import unittest
import shutil
import tempfile
import pytest
import os.path
import re
import sys
from xml.etree import ElementTree as ET

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import RobotTestFailure, TaskOptionsError
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.robotframework import Robot
from cumulusci.tasks.robotframework import RobotLibDoc
from cumulusci.tasks.robotframework import RobotTestDoc
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.robotframework.debugger import DebugListener
from cumulusci.tasks.robotframework.robotframework import KeywordLogger
from cumulusci.utils import touch

from cumulusci.tasks.robotframework.libdoc import KeywordFile


class TestRobot(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_run_task_with_failure(self, robot_run):
        robot_run.return_value = 1
        task = create_task(Robot, {"suites": "tests", "pdb": True})
        with self.assertRaises(RobotTestFailure):
            task()

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_run_task_error_message(self, robot_run):
        expected = {
            1: "1 test failed.",  # singular; pet peeve of my to see "1 tests"
            2: "2 tests failed.",  # plural
            249: "249 tests failed.",
            250: "250 or more tests failed.",
            251: "Help or version information printed.",
            252: "Invalid test data or command line options.",
            253: "Test execution stopped by user.",
            255: "Unexpected internal error",
        }
        for error_code in expected.keys():
            robot_run.return_value = error_code
            task = create_task(Robot, {"suites": "tests", "pdb": True})
            with self.assertRaises(RobotTestFailure) as error:
                task()
            self.assertEqual(str(error.exception), expected[error_code])

    @mock.patch("cumulusci.tasks.robotframework.robotframework.patch_statusreporter")
    def test_pdb_arg(self, patch_statusreporter):
        create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "pdb": "False",
            },
        )
        patch_statusreporter.assert_not_called()

        create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "pdb": "True",
            },
        )
        patch_statusreporter.assert_called_once()

    def test_list_args(self):
        """Verify that certain arguments are converted to lists"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "test": "one, two",
                "include": "foo, bar",
                "exclude": "a,  b",
                "vars": "uno, dos, tres",
            },
        )
        for option in ("test", "include", "exclude", "vars"):
            assert isinstance(task.options[option], list)

    def test_process_arg_requires_int(self):
        """Verify we throw a useful error for non-int "processes" option"""

        expected = "Please specify an integer for the `processes` option."
        with pytest.raises(TaskOptionsError, match=expected):
            create_task(Robot, {"suites": "tests", "processes": "bogus"})

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_process_arg_gt_zero(self, mock_subprocess_run, mock_robot_run):
        """Verify that setting the process option to a number > 1 runs pabot"""
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        task = create_task(Robot, {"suites": "tests", "processes": "2"})
        task()
        expected_cmd = [
            sys.executable,
            "-m",
            "pabot.pabot",
            "--pabotlib",
            "--processes",
            "2",
            "--variable",
            "org:test",
            "--outputdir",
            ".",
            "tests",
        ]
        mock_robot_run.assert_not_called()
        mock_subprocess_run.assert_called_once_with(expected_cmd)

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_process_arg_eq_zero(self, mock_subprocess_run, mock_robot_run):
        """Verify that setting the process option to 1 runs robot rather than pabot"""
        mock_robot_run.return_value = 0
        task = create_task(Robot, {"suites": "tests", "process": 0})
        task()
        mock_subprocess_run.assert_not_called()
        mock_robot_run.assert_called_once_with(
            "tests", listener=[], outputdir=".", variable=["org:test"]
        )

    def test_default_listeners(self):
        # first, verify that not specifying any listener options
        # results in no listeners...
        task = create_task(
            Robot, {"suites": "test"}  # required, or the task will raise an exception
        )
        assert len(task.options["options"]["listener"]) == 0

        # next, make sure that if we specify the options with a Falsy
        # string, the option is properly treated like a boolean
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "verbose": "False",
                "debug": "False",
            },
        )
        assert len(task.options["options"]["listener"]) == 0

    def test_debug_option(self):
        """Verify that setting debug to True attaches the appropriate listener"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "debug": "True",
            },
        )
        listener_classes = [
            listener.__class__ for listener in task.options["options"]["listener"]
        ]
        self.assertIn(
            DebugListener, listener_classes, "DebugListener was not in task options"
        )

    def test_verbose_option(self):
        """Verify that setting verbose to True attaches the appropriate listener"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "verbose": "True",
            },
        )
        listener_classes = [
            listener.__class__ for listener in task.options["options"]["listener"]
        ]
        self.assertIn(
            KeywordLogger, listener_classes, "KeywordLogger was not in task options"
        )

    def test_user_defined_listeners_option(self):
        """Verify that our listeners don't replace user-defined listeners"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "debug": "True",
                "verbose": "True",
                "options": {"listener": ["FakeListener.py"]},
            },
        )
        listener_classes = [
            listener.__class__ for listener in task.options["options"]["listener"]
        ]
        self.assertIn("FakeListener.py", task.options["options"]["listener"])
        self.assertIn(DebugListener, listener_classes)
        self.assertIn(KeywordLogger, listener_classes)


class TestRobotTestDoc(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.testdoc")
    def test_run_task(self, testdoc):
        task = create_task(RobotTestDoc, {"path": ".", "output": "out"})
        task()
        testdoc.assert_called_once_with(".", "out")


class TestRobotLibDoc(MockLoggerMixin, unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages
        self.datadir = os.path.dirname(__file__)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_output_directory_not_exist(self):
        """Verify we catch an error if the output directory doesn't exist"""
        path = os.path.join(self.datadir, "TestLibrary.py")
        output = os.path.join(self.tmpdir, "bogus", "index.html")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        # on windows, the output path may have backslashes which needs
        # to be protected in the expected regex
        expected = r"Unable to create output file '{}' (.*)".format(re.escape(output))
        with pytest.raises(TaskOptionsError, match=expected):
            task()

    def test_validate_filenames(self):
        """Verify that we catch bad filenames early"""
        expected = "Unable to find the following input files: 'bogus.py', 'bogus.robot'"
        output = os.path.join(self.tmpdir, "index.html")
        with pytest.raises(TaskOptionsError, match=expected):
            create_task(RobotLibDoc, {"path": "bogus.py,bogus.robot", "output": output})

        # there's a special path through the code if only one filename is bad...
        expected = "Unable to find the input file 'bogus.py'"
        with pytest.raises(TaskOptionsError, match=expected):
            create_task(RobotLibDoc, {"path": "bogus.py", "output": output})

    def test_task_log(self):
        """Verify that the task prints out the name of the output file"""
        path = os.path.join(self.datadir, "TestLibrary.py")
        output = os.path.join(self.tmpdir, "index.html")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        task()
        assert "created {}".format(output) in self.task_log["info"]
        assert os.path.exists(output)

    def test_comma_separated_list_of_files(self):
        """Verify that we properly parse a comma-separated list of files"""
        path = "{},{}".format(
            os.path.join(self.datadir, "TestLibrary.py"),
            os.path.join(self.datadir, "TestResource.robot"),
        )
        output = os.path.join(self.tmpdir, "index.html")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        task()
        assert os.path.exists(output)
        assert len(task.result["files"]) == 2

    def test_glob_patterns(self):
        output = os.path.join(self.tmpdir, "index.html")
        path = os.path.join(self.datadir, "*Library.py")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        task()
        assert os.path.exists(output)
        assert len(task.result["files"]) == 1
        assert task.result["files"][0] == os.path.join(self.datadir, "TestLibrary.py")

    def test_remove_duplicates(self):
        output = os.path.join(self.tmpdir, "index.html")
        path = os.path.join(self.datadir, "*Library.py")
        task = create_task(RobotLibDoc, {"path": [path, path], "output": output})
        task()
        assert len(task.result["files"]) == 1
        assert task.result["files"][0] == os.path.join(self.datadir, "TestLibrary.py")

    def test_creates_output(self):
        path = os.path.join(self.datadir, "TestLibrary.py")
        output = os.path.join(self.tmpdir, "index.html")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        task()
        assert "created {}".format(output) in self.task_log["info"]
        assert os.path.exists(output)

    def test_pageobject(self):
        """Verify that we can parse a page object file"""
        path = os.path.join(self.datadir, "TestPageObjects.py")
        output = os.path.join(self.tmpdir, "index.html")
        task = create_task(RobotLibDoc, {"path": path, "output": output})
        task()
        assert "created {}".format(output) in self.task_log["info"]
        assert os.path.exists(output)


class TestRobotLibDocKeywordFile(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_existing_file(self):
        path = os.path.join(self.tmpdir, "keywords.py")
        touch(path)
        kwfile = KeywordFile(path)
        assert kwfile.filename == "keywords.py"
        assert kwfile.path == path
        assert kwfile.keywords == {}

    def test_file_as_module(self):
        kwfile = KeywordFile("cumulusci.robotframework.Salesforce")
        assert kwfile.filename == "Salesforce"
        assert kwfile.path == "cumulusci.robotframework.Salesforce"
        assert kwfile.keywords == {}

    def test_add_keyword(self):
        kwfile = KeywordFile("test.TestLibrary")
        kwfile.add_keywords("the documentation...", ("Detail", "Contact"))
        assert len(kwfile.keywords) == 1
        assert kwfile.keywords[("Detail", "Contact")] == "the documentation..."


class TestRobotLibDocOutput(unittest.TestCase):
    """Tests for the generated robot keyword documentation"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.datadir = os.path.dirname(__file__)
        path = [
            os.path.join(self.datadir, "TestLibrary.py"),
            os.path.join(self.datadir, "TestResource.robot"),
        ]
        output = os.path.join(self.tmpdir, "index.html")
        self.task = create_task(
            RobotLibDoc,
            {"path": path, "output": output, "title": "Keyword Documentation, yo."},
        )
        self.task()
        docroot = ET.parse(output).getroot()
        self.html_body = docroot.find("body")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_output_title(self):
        """Verify the document has the expected title"""
        title_element = self.html_body.find(
            ".//div[@class='header']/h1[@class='title']"
        )
        assert title_element is not None
        assert title_element.text.strip() == "Keyword Documentation, yo."

    def test_formatted_documentation(self):
        """Verify that markup in the documentation is rendered as html"""
        doc_element = self.html_body.find(
            ".//tr[@id='TestLibrary.py.Library Keyword One']//td[@class='kwdoc']"
        )
        doc_html = str(ET.tostring(doc_element, method="html").strip())
        # we could just do an assert on the full markup of the
        # element, but it seems likely that could fail for benign
        # regions (extra whitespace, for example). So we'll just make
        # sure there are a couple of expected formatted elements.
        assert "<b>bold</b>" in doc_html
        assert "<i>italics</i>" in doc_html

    def test_output_sections(self):
        """Verify that the output has a section for each file"""
        sections = self.html_body.findall(".//div[@class='file']")
        section_titles = [
            x.find(".//div[@class='file-header']/h2").text for x in sections
        ]
        assert len(sections) == 2, "expected to find 2 sections, found {}".format(
            len(sections)
        )
        assert section_titles == ["TestLibrary.py", "TestResource.robot"]

    def test_output_keywords(self):
        """Verify that all keywords in the libraries are represented in the output file"""
        keyword_rows = self.html_body.findall(".//tr[@class='kwrow']")
        keywords = [x.find(".//td[@class='kwname']") for x in keyword_rows]
        keyword_names = [x.text.strip() for x in keywords]
        assert len(keywords) == 4
        assert keyword_names == [
            "Library Keyword One",
            "Library Keyword Two",
            "Resource keyword one",
            "Resource keyword two",
        ]


class TestLibdocPageObjects(unittest.TestCase):
    """Tests for generating docs for page objects"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.datadir = os.path.dirname(__file__)
        path = [os.path.join(self.datadir, "TestPageObjects.py")]
        self.output = os.path.join(self.tmpdir, "index.html")
        self.task = create_task(
            RobotLibDoc,
            {"path": path, "output": self.output, "title": "Keyword Documentation, yo"},
        )
        self.task()

        self.docroot = ET.parse(self.output).getroot()
        self.html_body = self.docroot.find("body")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_file_title(self):
        """Verify that the TITLE in the file is added to the generated html"""
        # The page object file has a TITLE attribute and a docstring;
        # make sure they are picked up.
        title_element = self.html_body.find(".//div[@class='file-header']/h2")
        assert title_element.text == "This is the title"

    def test_file_description(self):
        """Verify that the docstring in the file is added to the generated html"""
        file_doc_element = self.html_body.find(
            ".//div[@class='pageobject-file-description']"
        )
        description = ET.tostring(file_doc_element).decode("utf-8").strip()
        assert (
            description
            == '<div class="pageobject-file-description"><p>this is the docstring</p></div>'
        )

    def test_pageobject_sections(self):
        # the TestPageObjects.py file has two page objects,
        # one with two keywords and one with three
        sections = self.html_body.findall(".//div[@class='pageobject-header']")
        assert len(sections) == 2

    def test_pageobject_docstring(self):
        section = self.html_body.find(".//div[@pageobject='Detail-Something__c']")
        description = section.find("div[@class='description']")
        expected = '<div class="description" title="Description"><p>Description of SomethingDetailPage</p></div>'
        actual = ET.tostring(description).decode("utf-8").strip()
        assert actual == expected

        section = self.html_body.find(".//div[@pageobject='Listing-Something__c']")
        description = section.find("div[@class='description']")
        expected = '<div class="description" title="Description"><p>Description of SomethingListingPage</p></div>'
        actual = ET.tostring(description).decode("utf-8").strip()
        assert actual == expected
