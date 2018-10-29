import pdb
import sys

from robot import run as robot_run
from robot.libdoc import libdoc
from robot.libraries.BuiltIn import BuiltIn
from robot.testdoc import testdoc

from cumulusci.core.exceptions import RobotTestFailure
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.robotframework.utils import set_pdb_trace
from cumulusci.tasks.salesforce import BaseSalesforceTask


class Robot(BaseSalesforceTask):
    task_options = {
        "suites": {
            "description": 'Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory',
            "required": True,
        },
        "tests": {
            "description": "Run only tests matching name patterns.  Can be comma separated and use robot wildcards like *"
        },
        "include": {"description": "Includes tests with a given tag"},
        "exclude": {"description": "Excludes tests with a given tag"},
        "vars": {
            "description": "Pass values to override variables in the format VAR1:foo,VAR2:bar"
        },
        "xunit": {"description": "Set an XUnit format output file for test results"},
        "options": {
            "description": "A dictionary of options to robot.run method.  See docs here for format.  NOTE: There is no cci CLI support for this option since it requires a dictionary.  Use this option in the cumulusci.yml when defining custom tasks where you can easily create a dictionary in yaml."
        },
        "pdb": {"description": "If true, run the Python debugger when tests fail."},
        "verbose": {"description": "If true, log each keyword as it runs."},
    }

    def _init_options(self, kwargs):
        super(Robot, self)._init_options(kwargs)

        for option in ("tests", "include", "exclude", "vars"):
            if option in self.options:
                self.options[option] = process_list_arg(self.options[option])
        if "vars" not in self.options:
            self.options["vars"] = []
        self.options["vars"].append("org:{}".format(self.org_config.name))

        # Initialize options as a dict
        if "options" not in self.options:
            self.options["options"] = {}

        if process_bool_arg(self.options.get("verbose")):
            self.options["options"]["listener"] = KeywordLogger

        if process_bool_arg(self.options.get("pdb")):
            patch_statusreporter()

    def _run_task(self):
        options = self.options["options"].copy()
        for option in ("tests", "include", "exclude", "xunit"):
            if option in self.options:
                options[option] = self.options[option]
        options["variable"] = self.options.get("vars") or []

        num_failed = robot_run(self.options["suites"], **options)
        if num_failed:
            raise RobotTestFailure("{} tests failed".format(num_failed))


class RobotLibDoc(BaseTask):
    task_options = {
        "path": {
            "description": "The path to the robot library to be documented.  Can be a python file or a .robot file.",
            "required": True,
        },
        "output": {
            "description": "The output file where the documentation will be written",
            "required": True,
        },
    }

    def _run_task(self):
        return libdoc(self.options["path"], self.options["output"])


class RobotTestDoc(BaseTask):
    task_options = {
        "path": {
            "description": "The path containing .robot test files",
            "required": True,
        },
        "output": {
            "description": "The output html file where the documentation will be written",
            "required": True,
        },
    }

    def _run_task(self):
        return testdoc(self.options["path"], self.options["output"])


class KeywordLogger(object):
    ROBOT_LISTENER_API_VERSION = 2

    def start_keyword(name, attrs):
        sys.stdout.write("  {}  {}\n".format(attrs["kwname"], "  ".join(attrs["args"])))
        sys.stdout.flush()


def patch_statusreporter():
    """Monkey patch robotframework to do postmortem debugging
    """
    from robot.running.statusreporter import StatusReporter

    orig_exit = StatusReporter.__exit__

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and isinstance(exc_val, Exception):
            set_pdb_trace(pm=True)
        return orig_exit(self, exc_type, exc_val, exc_tb)

    StatusReporter.__exit__ = __exit__
