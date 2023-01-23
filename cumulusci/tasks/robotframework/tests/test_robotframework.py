import csv
import os.path
import re
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from unittest import mock
from xml.etree import ElementTree as ET

import pytest
import responses
from robot.libdocpkg.robotbuilder import LibraryDocBuilder

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.exceptions import RobotTestFailure, TaskOptionsError
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.robotframework import Robot, RobotLibDoc, RobotTestDoc
from cumulusci.tasks.robotframework.debugger import DebugListener
from cumulusci.tasks.robotframework.libdoc import KeywordFile
from cumulusci.tasks.robotframework.robotframework import KeywordLogger
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.utils import temporary_dir, touch
from cumulusci.utils.xml.robot_xml import log_perf_summary_from_xml


class TestRobot:
    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_run_task_with_failure(self, robot_run):
        robot_run.return_value = 1
        task = create_task(Robot, {"suites": "tests", "pdb": True})
        with pytest.raises(RobotTestFailure):
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
            with pytest.raises(RobotTestFailure) as e:
                task()
            assert str(e.value) == expected[error_code]

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
                "skip": "xyzzy,plugh",
            },
        )
        for option in ("test", "include", "exclude", "vars", "suites", "skip"):
            assert isinstance(task.options[option], list)

    def test_options_converted_to_dict(self):
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "options": "outputdir:/tmp/example,loglevel:DEBUG",
            },
        )
        assert isinstance(task.options["options"], dict)

    def test_process_arg_requires_int(self):
        """Verify we throw a useful error for non-int "processes" option"""

        expected = "Please specify an integer for the `processes` option."
        with pytest.raises(TaskOptionsError, match=expected):
            create_task(Robot, {"suites": "tests", "processes": "bogus"})

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_pabot_arg_with_process_eq_one(self, mock_subprocess_run, mock_robot_run):
        """Verify that pabot-specific arguments are ignored if processes==1"""
        mock_robot_run.return_value = 0
        task = create_task(
            Robot,
            {
                "suites": "tests",
                "process": 1,
                "ordering": "robot/order.txt",
                "testlevelsplit": "true",
            },
        )
        task()
        mock_subprocess_run.assert_not_called()
        outputdir = str(Path(".").resolve())
        mock_robot_run.assert_called_once_with(
            "tests",
            listener=[],
            outputdir=outputdir,
            variable=["org:test"],
            tagstatexclude=["cci_metric_elapsed_time", "cci_metric"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_process_arg_eq_one(self, mock_subprocess_run, mock_robot_run):
        """Verify that setting the process option to 1 runs robot rather than pabot"""
        mock_robot_run.return_value = 0
        task = create_task(Robot, {"suites": "tests", "process": 1})
        task()
        mock_subprocess_run.assert_not_called()
        outputdir = str(Path(".").resolve())
        mock_robot_run.assert_called_once_with(
            "tests",
            listener=[],
            outputdir=outputdir,
            variable=["org:test"],
            tagstatexclude=["cci_metric_elapsed_time", "cci_metric"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_suites(self, mock_robot_run):
        """Verify that passing a list of suites is handled properly"""
        mock_robot_run.return_value = 0
        task = create_task(Robot, {"suites": "tests,more_tests", "process": 1})
        task()
        outputdir = str(Path(".").resolve())
        mock_robot_run.assert_called_once_with(
            "tests",
            "more_tests",
            listener=[],
            outputdir=outputdir,
            variable=["org:test"],
            tagstatexclude=["cci_metric_elapsed_time", "cci_metric"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_tagstatexclude(self, mock_robot_run):
        """Verify tagstatexclude is treated as a list"""
        mock_robot_run.return_value = 0
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "options": {
                    "tagstatexclude": "this,that",
                },
            },
        )
        assert type(task.options["options"]["tagstatexclude"]) == list
        task()
        outputdir = str(Path(".").resolve())
        mock_robot_run.assert_called_once_with(
            "test",
            listener=[],
            outputdir=outputdir,
            variable=["org:test"],
            tagstatexclude=["this", "that", "cci_metric_elapsed_time", "cci_metric"],
            stdout=sys.stdout,
            stderr=sys.stderr,
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
                "robot_debug": "False",
            },
        )
        assert len(task.options["options"]["listener"]) == 0

    def test_debug_option(self):
        """Verify that setting debug to True attaches the appropriate listener"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "robot_debug": "True",
            },
        )
        listener_classes = [
            listener.__class__ for listener in task.options["options"]["listener"]
        ]
        assert (
            DebugListener in listener_classes
        ), "DebugListener was not in task options"

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
        assert (
            KeywordLogger in listener_classes
        ), "KeywordLogger was not in task options"

    def test_user_defined_listeners_option(self):
        """Verify that our listeners don't replace user-defined listeners"""
        task = create_task(
            Robot,
            {
                "suites": "test",  # required, or the task will raise an exception
                "robot_debug": "True",
                "verbose": "True",
                "options": {"listener": ["FakeListener.py"]},
            },
        )
        listener_classes = [
            listener.__class__ for listener in task.options["options"]["listener"]
        ]
        assert "FakeListener.py" in task.options["options"]["listener"]
        assert DebugListener in listener_classes
        assert KeywordLogger in listener_classes

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch(
        "cumulusci.tasks.robotframework.robotframework.pythonpathsetter.add_path"
    )
    def test_sources(self, mock_add_path, mock_robot_run):
        """Verify that sources get added to PYTHONPATH when task runs"""
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(
            universal_config,
            {
                "sources": {
                    "test1": {"path": "dummy1"},
                    "test2": {"path": "dummy2"},
                }
            },
        )
        # get_namespace returns a config. The only part of the config
        # that the code uses is the repo_root property, so we don't need
        # a full blown config.
        project_config.get_namespace = mock.Mock(
            side_effect=lambda source: mock.Mock(
                repo_root=project_config.sources[source]["path"]
            )
        )

        task = create_task(
            Robot,
            {"suites": "test", "sources": ["test1", "test2"]},
            project_config=project_config,
        )

        mock_robot_run.return_value = 0
        assert "dummy1" not in sys.path
        assert "dummy2" not in sys.path
        task()
        project_config.get_namespace.assert_has_calls(
            [mock.call("test1"), mock.call("test2")]
        )
        mock_add_path.assert_has_calls(
            [mock.call("dummy1", end=True), mock.call("dummy2", end=True)]
        )
        assert "dummy1" not in sys.path
        assert "dummy2" not in sys.path
        assert (
            Path(".").resolve() == Path(task.return_values["robot_outputdir"]).resolve()
        )

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch(
        "cumulusci.tasks.robotframework.robotframework.pythonpathsetter.add_path"
    )
    def test_repo_root_in_sys_path(self, mock_add_path, mock_robot_run):
        """Verify that the repo root is added to sys.path

        Normally, the repo root is added to sys.path in the __init__
        of BaseSalesforceTask. However, if we're running a task from
        another repo, the git root of that other repo isn't added. The
        robot task will do that; this verifies that.

        """
        mock_robot_run.return_value = 0
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        with temporary_dir() as d:
            project_config.repo_info["root"] = d
            task = create_task(
                Robot, {"suites": "tests"}, project_config=project_config
            )
            assert d not in sys.path
            task()
            mock_add_path.assert_called_once_with(d)
            assert d not in sys.path

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_sources_not_found(self, mock_robot_run):
        task = create_task(
            Robot,
            {"suites": "test", "sources": ["bogus"]},
        )

        expected = "robot source 'bogus' could not be found"
        with pytest.raises(TaskOptionsError, match=expected):
            task()


@mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
def test_outputdir_return_value(mock_run, tmpdir):
    """Ensure that the task properly sets the outputdir return value"""
    project_config = BaseProjectConfig(UniversalConfig())

    test_dir = "test-dir"
    tmpdir.mkdir(test_dir)
    task = create_task(
        Robot,
        {
            "suites": "test",
            "options": {"outputdir": test_dir},
        },
        project_config=project_config,
    )
    mock_run.return_value = 0
    task()
    assert (Path.cwd() / test_dir).resolve() == Path(
        task.return_values["robot_outputdir"]
    ).resolve()


class TestRobotTestDoc:
    @mock.patch("cumulusci.tasks.robotframework.robotframework.testdoc")
    def test_run_task(self, testdoc):
        task = create_task(RobotTestDoc, {"path": ".", "output": "out"})
        task()
        testdoc.assert_called_once_with(".", "out")


class TestRobotLibDoc(MockLoggerMixin):
    maxDiff = None

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages
        self.datadir = os.path.dirname(__file__)

    def teardown_method(self):
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

    def test_csv(self):
        path = ",".join(
            (
                os.path.join(self.datadir, "TestLibrary.py"),
                os.path.join(self.datadir, "TestResource.robot"),
                os.path.join(self.datadir, "TestPageObjects.py"),
            )
        )
        output = Path(self.tmpdir) / "keywords.csv"
        if output.exists():
            os.remove(output)
        task = create_task(RobotLibDoc, {"path": path, "output": output.as_posix()})
        task()
        assert os.path.exists(output)
        with open(output, "r", newline="") as csvfile:
            reader = csv.reader(csvfile)
            actual_output = [row for row in reader]

        # not only does this verify that the expected keywords are in
        # the output, but that the base class keywords are *not*
        datadir = os.path.join("cumulusci", "tasks", "robotframework", "tests", "")
        expected_output = [
            ["Name", "Source", "Line#", "po type", "po_object", "Documentation"],
            [
                "Keyword One",
                f"{datadir}TestPageObjects.py",
                "13",
                "Listing",
                "Something__c",
                "",
            ],
            [
                "Keyword One",
                f"{datadir}TestPageObjects.py",
                "24",
                "Detail",
                "Something__c",
                "",
            ],
            [
                "Keyword Three",
                f"{datadir}TestPageObjects.py",
                "30",
                "Detail",
                "Something__c",
                "",
            ],
            [
                "Keyword Two",
                f"{datadir}TestPageObjects.py",
                "16",
                "Listing",
                "Something__c",
                "",
            ],
            [
                "Keyword Two",
                f"{datadir}TestPageObjects.py",
                "27",
                "Detail",
                "Something__c",
                "",
            ],
            [
                "Library Keyword One",
                f"{datadir}TestLibrary.py",
                "13",
                "",
                "",
                "Keyword documentation with *bold* and _italics_",
            ],
            [
                "Library Keyword Two",
                f"{datadir}TestLibrary.py",
                "17",
                "",
                "",
                "",
            ],
            [
                "Resource keyword one",
                f"{datadir}TestResource.robot",
                "2",
                "",
                "",
                "",
            ],
            [
                "Resource keyword two",
                f"{datadir}TestResource.robot",
                "6",
                "",
                "",
                "",
            ],
        ]

        assert actual_output == expected_output

    @mock.patch("cumulusci.tasks.robotframework.libdoc.view_file")
    def test_preview_option(self, mock_view_file):
        """Verify that the 'preview' option results in calling the view_file method"""
        path = os.path.join(self.datadir, "TestLibrary.py")
        output = os.path.join(self.tmpdir, "index.html")
        task = create_task(
            RobotLibDoc, {"path": path, "output": output, "preview": True}
        )
        task()
        mock_view_file.assert_called_once_with(output)


class TestRobotLibDocKeywordFile:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp(dir=".")

    def teardown_method(self):
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

    def test_to_tuples(self):
        """Test that to_tuples returns relative paths when possible

        The code attempts to convert absolute paths to relative paths,
        but if it can't then the path remains unchainged. This test generates
        results with one file that is relative to cwd and one that is not.
        """

        here = os.path.dirname(__file__)
        path = Path(here) / "TestLibrary.py"
        libdoc = LibraryDocBuilder().build(str(path))

        # we'll set the first to a non-relative directory and leave
        # the other one relative to here (assuming that `here` is
        # relative to cwd)
        absolute_path = str(Path("/bogus/whatever.py"))
        libdoc.keywords[0].source = absolute_path

        # The returned result is a set, so the order is indeterminate. That's
        # why the following line sorts it.
        kwfile = KeywordFile("Whatever")
        kwfile.add_keywords(libdoc)
        rows = sorted(kwfile.to_tuples())

        # verify the absolute path remains absolute
        assert rows[0][1] == absolute_path
        # verify that the path to a file under cwd is relative
        assert rows[1][1] == str(path.relative_to(os.getcwd()))


class TestRobotLibDocOutput:
    """Tests for the generated robot keyword documentation"""

    def setup_method(self):
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

    def teardown_method(self):
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
            ".//tr[@id='TestLibrary.py.Library-Keyword-One']//td[@class='kwdoc']"
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


class TestLibdocPageObjects:
    """Tests for generating docs for page objects"""

    def setup_method(self):
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

    def teardown_method(self):
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
        assert shrinkws(actual) == shrinkws(expected)

        section = self.html_body.find(".//div[@pageobject='Listing-Something__c']")
        description = section.find("div[@class='description']")
        expected = '<div class="description" title="Description"><p>Description of SomethingListingPage</p></div>'
        actual = ET.tostring(description).decode("utf-8").strip()
        assert shrinkws(actual) == shrinkws(expected)


class TestRobotPerformanceKeywords:
    def setup(self):
        self.datadir = os.path.dirname(__file__)

    @contextmanager
    def _run_robot_and_parse_xml(
        self, test_pattern, suite_path="tests/salesforce/performance.robot"
    ):
        universal_config = UniversalConfig()
        project_config = BaseProjectConfig(universal_config)
        with temporary_dir() as d, mock.patch(
            "cumulusci.robotframework.Salesforce.Salesforce._init_locators"
        ), responses.RequestsMock():
            project_config.repo_info["root"] = d
            suite = Path(self.datadir) / "../../../robotframework/" / suite_path
            task = create_task(
                Robot,
                {
                    "test": test_pattern,
                    "suites": str(suite),
                    "options": {"outputdir": d, "skiponfailure": "noncritical"},
                },
                project_config=project_config,
            )
            task()
            logger_func = mock.Mock()
            log_perf_summary_from_xml(Path(d) / "output.xml", logger_func)
            yield logger_func.mock_calls

    def parse_metric(self, metric):
        name, value = metric.split(": ")
        value = value.strip("s ")  # strip seconds unit
        try:
            value = float(value)
        except ValueError:
            raise Exception(f"Cannot convert to float {value}")
        return name.strip(), value

    def extract_times(self, pattern, call):
        first_arg = call[1][0]
        if pattern in first_arg:
            metrics = first_arg.split("-")[-1].split(",")
            return dict(self.parse_metric(metric) for metric in metrics)

    def test_parser_FOR_and_IF(self):
        # verify that metrics nested inside a FOR or IF are accounted for
        pattern = "Test FOR and IF statements"
        suite_path = Path(self.datadir) / "performance.robot"
        with self._run_robot_and_parse_xml(
            pattern, suite_path=suite_path
        ) as logger_calls:
            elapsed_times = [self.extract_times(pattern, call) for call in logger_calls]
            perf_data = list(filter(None, elapsed_times))[0]
            assert perf_data["plugh"] == 4.0
            assert perf_data["xyzzy"] == 2.0

    def test_elapsed_time_xml(self):
        pattern = "Elapsed Time: "

        with self._run_robot_and_parse_xml("Test Perf*") as logger_calls:
            elapsed_times = [self.extract_times(pattern, call) for call in logger_calls]
            elapsed_times = [next(iter(x.values())) for x in elapsed_times if x]
            elapsed_times.sort()

            assert elapsed_times[1:] == [53, 11655.9, 18000.0]
            assert float(elapsed_times[0]) < 3

    def test_metrics(self):
        pattern = "Max_CPU_Percent: "
        with self._run_robot_and_parse_xml(
            "Test Perf Measure Other Metric"
        ) as logger_calls:
            elapsed_times = [self.extract_times(pattern, call) for call in logger_calls]
            assert list(filter(None, elapsed_times))[0]["Max_CPU_Percent"] == 30.0

    def test_empty_test(self):
        pattern = "Max_CPU_Percent: "
        with self._run_robot_and_parse_xml(
            "Test Perf Measure Other Metric"
        ) as logger_calls:
            elapsed_times = [self.extract_times(pattern, call) for call in logger_calls]
            assert list(filter(None, elapsed_times))[0]["Max_CPU_Percent"] == 30.0

    def test_explicit_failures(self):
        pattern = "Elapsed Time: "
        suite_path = Path(self.datadir) / "failing_tests.robot"
        with self._run_robot_and_parse_xml(
            "Test *", suite_path=suite_path
        ) as logger_calls:
            elapsed_times = [self.extract_times(pattern, call) for call in logger_calls]
            assert list(filter(None, elapsed_times)) == [
                {"Elapsed Time": 11655.9, "Donuts": 42.3}
            ]


def shrinkws(s):
    return re.sub(r"\s+", " ", s).replace("> <", "><")
