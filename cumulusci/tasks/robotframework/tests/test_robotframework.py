import mock
import unittest
import shutil
import tempfile
import pytest
import os.path
from xml.etree import ElementTree as ET

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import RobotTestFailure, TaskOptionsError
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.robotframework import Robot
from cumulusci.tasks.robotframework import RobotLibDoc
from cumulusci.tasks.robotframework import RobotTestDoc
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRobot(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_run_task(self, robot_run):
        robot_run.return_value = 1
        task = create_task(Robot, {"suites": "tests", "pdb": True})
        with self.assertRaises(RobotTestFailure):
            task()


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

    def test_validate_filenames(self):
        """Verify that we catch bad filenames early"""
        expected = "Unable to find the following input files: 'bogus.py', 'bogus.robot'"
        output = os.path.join(self.tmpdir, "index.html")
        with pytest.raises(TaskOptionsError, match=expected):
            create_task(RobotLibDoc, {"path": "bogus.py,bogus.robot", "output": output})

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

    def test_pageobject_sections(self):
        # the TestPageObjects.py file has two page objects,
        # one with two keywords and one with three
        sections = self.html_body.findall(".//div[@class='pageobject-header']")
        assert len(sections) == 2

    def test_pageobject_docstring(self):
        section = self.html_body.find(".//div[@pageobject='Detail-Something__c']")
        description = section.find("div[@class='description']")
        expected = (
            '<div class="description"><p>Description of SomethingDetailPage</p></div>'
        )
        actual = ET.tostring(description).decode("utf-8").strip()
        assert actual == expected

        section = self.html_body.find(".//div[@pageobject='Listing-Something__c']")
        description = section.find("div[@class='description']")
        expected = (
            '<div class="description"><p>Description of SomethingListingPage</p></div>'
        )
        actual = ET.tostring(description).decode("utf-8").strip()
        assert actual == expected
