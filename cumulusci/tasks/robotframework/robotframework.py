import os
import shlex
import sys
import subprocess

from robot import run as robot_run
from robot import pythonpathsetter
from robot.testdoc import testdoc

from cumulusci.core.exceptions import (
    RobotTestFailure,
    TaskOptionsError,
    NamespaceNotFoundError,
)
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.robotframework.utils import set_pdb_trace
from cumulusci.tasks.salesforce import BaseSalesforceTask
from cumulusci.tasks.robotframework.debugger import DebugListener


class Robot(BaseSalesforceTask):
    task_options = {
        "suites": {
            "description": 'Paths to test case files/directories to be executed similarly as when running the robot command on the command line.  Defaults to "tests" to run all tests in the tests directory',
            "required": True,
        },
        "test": {
            "description": "Run only tests matching name patterns.  Can be comma separated and use robot wildcards like *"
        },
        "include": {"description": "Includes tests with a given tag"},
        "exclude": {"description": "Excludes tests with a given tag"},
        "vars": {
            "description": "Pass values to override variables in the format VAR1:foo,VAR2:bar"
        },
        "xunit": {"description": "Set an XUnit format output file for test results"},
        "sources": {
            "description": "List of sources defined in cumulusci.yml that are required by the robot task.",
            "required": False,
        },
        "options": {
            "description": "A dictionary of options to robot.run method.  See docs here for format.  NOTE: There is no cci CLI support for this option since it requires a dictionary.  Use this option in the cumulusci.yml when defining custom tasks where you can easily create a dictionary in yaml."
        },
        "name": {"description": "Sets the name of the top level test suite"},
        "pdb": {"description": "If true, run the Python debugger when tests fail."},
        "verbose": {"description": "If true, log each keyword as it runs."},
        "debug": {
            "description": "If true, enable the `breakpoint` keyword to enable the robot debugger"
        },
        "processes": {
            "description": "*experimental* Number of processes to use for running tests in parallel. If this value is set to a number larger than 1 the tests will run using the open source tool pabot rather than robotframework. For example, -o parallel 2 will run half of the tests in one process and half in another. If not provided, all tests will run in a single process using the standard robot test runner.",
            "default": "1",
        },
    }

    def _init_options(self, kwargs):
        super(Robot, self)._init_options(kwargs)

        for option in ("test", "include", "exclude", "vars", "sources", "suites"):
            if option in self.options:
                self.options[option] = process_list_arg(self.options[option])
        if "vars" not in self.options:
            self.options["vars"] = []

        # Initialize options as a dict
        if "options" not in self.options:
            self.options["options"] = {}

        # processes needs to be an integer.
        try:
            self.options["processes"] = int(self.options.get("processes", 1))
        except (TypeError, ValueError):
            raise TaskOptionsError(
                "Please specify an integer for the `processes` option."
            )

        # There are potentially many robot options that are or could
        # be lists, but the only one we currently care about is the
        # listener option since we may need to append additional values
        # onto it.
        for option in ("listener",):
            if option in self.options["options"]:
                self.options["options"][option] = process_list_arg(
                    self.options["options"][option]
                )

        listeners = self.options["options"].setdefault("listener", [])

        if process_bool_arg(self.options.get("verbose") or False):
            listeners.append(KeywordLogger())

        if process_bool_arg(self.options.get("debug") or False):
            listeners.append(DebugListener())

        if process_bool_arg(self.options.get("pdb") or False):
            patch_statusreporter()

        self.options.setdefault("sources", [])

    def _run_task(self):
        self.options["vars"].append("org:{}".format(self.org_config.name))
        options = self.options["options"].copy()
        for option in ("test", "include", "exclude", "xunit", "name"):
            if option in self.options:
                options[option] = self.options[option]
        options["variable"] = self.options.get("vars") or []
        options["outputdir"] = os.path.relpath(
            os.path.join(self.working_path, options.get("outputdir", ".")), os.getcwd()
        )
        # Set as a return value so other things that want to use
        # this file (e.g. MetaCI) know where it is
        self.return_values["robot_outputdir"] = options["outputdir"]

        # get_namespace will potentially download sources that have
        # yet to be downloaded. For these downloaded sources we'll add
        # the cached directories to PYTHONPATH before running.
        source_paths = {}
        for source in self.options["sources"]:
            try:
                source_config = self.project_config.get_namespace(source)
                source_paths[source] = source_config.repo_root
            except NamespaceNotFoundError:
                raise TaskOptionsError(f"robot source '{source}' could not be found")

        # replace namespace prefixes with path to cached folder
        for i, path in enumerate(self.options["suites"]):
            prefix, _, path = path.rpartition(":")
            if prefix in source_paths:
                self.options["suites"][i] = os.path.join(source_paths[prefix], path)

        if self.options["processes"] > 1:
            # Since pabot runs multiple robot processes, and because
            # those processes aren't cci tasks, we have to set up the
            # environment to match what we do with a cci task. Specifically,
            # we need to add the repo root to PYTHONPATH (via the --pythonpath
            # option). Otherwise robot won't be able to find libraries and
            # resource files referenced as relative to the repo root
            cmd = [
                sys.executable,
                "-m",
                "pabot.pabot",
                "--pabotlib",
                "--processes",
                str(self.options["processes"]),
                "--pythonpath",
                str(self.project_config.repo_root),
            ]
            # We need to convert options to their commandline equivalent
            for option, value in options.items():
                if isinstance(value, list):
                    for item in value:
                        cmd.extend([f"--{option}", str(item)])
                else:
                    cmd.extend([f"--{option}", str(value)])

            # Add each source to pythonpath. Use --pythonpath since
            # pybot will need to use that option for each process that
            # it spawns.
            for path in source_paths.values():
                cmd.extend(["--pythonpath", path])

            cmd.extend(self.options["suites"])
            self.logger.info(
                f"pabot command: {' '.join([shlex.quote(x) for x in cmd])}"
            )
            result = subprocess.run(cmd)
            num_failed = result.returncode

        else:
            # Save it so that we can restore it later
            orig_sys_path = sys.path.copy()

            # Add each source to PYTHONPATH. Robot recommends that we
            # use pythonpathsetter instead of directly setting
            # sys.path. <shrug>
            for path in source_paths.values():
                pythonpathsetter.add_path(path, end=True)

            # Make sure the path to the repo root is on sys.path. Normally
            # it will be, but if we're running this task from another repo
            # it might not be.
            #
            # Note: we can't just set the pythonpath option; that
            # option is specifically called out as not being supported
            # by robot.run. Plus, robot recommends we call a special
            # function instead of directly modifying sys.path
            if self.project_config.repo_root not in sys.path:
                pythonpathsetter.add_path(self.project_config.repo_root)

            try:
                num_failed = robot_run(*self.options["suites"], **options)
            finally:
                sys.path = orig_sys_path

        # These numbers are from the robot framework user guide:
        # http://robotframework.org/robotframework/latest/RobotFrameworkUserGuide.html#return-codes
        if 0 < num_failed < 250:
            raise RobotTestFailure(
                f"{num_failed} test{'' if num_failed == 1 else 's'} failed."
            )
        elif num_failed == 250:
            raise RobotTestFailure("250 or more tests failed.")
        elif num_failed == 251:
            raise RobotTestFailure("Help or version information printed.")
        elif num_failed == 252:
            raise RobotTestFailure("Invalid test data or command line options.")
        elif num_failed == 253:
            raise RobotTestFailure("Test execution stopped by user.")
        elif num_failed >= 255:
            raise RobotTestFailure("Unexpected internal error")


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

    def start_keyword(self, name, attrs):
        sys.stdout.write("  {}  {}\n".format(attrs["kwname"], "  ".join(attrs["args"])))
        sys.stdout.flush()


def patch_statusreporter():
    """Monkey patch robotframework to do postmortem debugging"""
    from robot.running.statusreporter import StatusReporter

    orig_exit = StatusReporter.__exit__

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val and isinstance(exc_val, Exception):
            set_pdb_trace(pm=True)
        return orig_exit(self, exc_type, exc_val, exc_tb)

    StatusReporter.__exit__ = __exit__


def patch_executescript():
    # convert executeScript calls into executeAsyncScript
    # to work around an issue in chromedriver 77
    # https://bugs.chromium.org/p/chromedriver/issues/detail?id=3103
    from selenium.webdriver.remote.webdriver import WebDriver

    def execute_script(self, script, *args):
        # the last argument is the function called to say the async operation is done
        script = (
            "arguments[arguments.length - 1](function(){"
            + script
            + "}.apply(null, Array.prototype.slice.call(arguments, 0, -1)));"
        )
        return self.execute_async_script(script, *args)

    WebDriver.execute_script = execute_script


patch_executescript()
