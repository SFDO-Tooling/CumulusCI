from pathlib import Path
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg
from cumulusci.core.utils import process_list_arg
from cumulusci.core.exceptions import CumulusCIFailure
import rflint
import glob
import os


class RobotLint(BaseTask):
    task_docs = """
    The robot_lint task performs static analysis on one or more .robot
    and .resource files. Each line is parsed, and the result passed through
    a series of rules. Rules can issue warnings or errors about each line.

    If any errors are reported, the task will exit with a non-zero status.

    When a rule has been violated, a line will appear on the output in
    the following format:

    *<severity>*: *<line>*, *<character>*: *<description>* (*<name>*)

    - *<severity>* will be either W for warning or E for error
    - *<line>* is the line number where the rule was triggered
    - *<character>* is the character where the rule was triggered,
      or 0 if the rule applies to the whole line
    - *<description>* is a short description of the issue
    - *<name>* is the name of the rule that raised the issue

    Note: the rule name can be used with the ignore, warning, error,
    and configure options.

    Some rules are configurable, and can be configured with the
    `configure` option. This option takes a list of values in the form
    *<rule>*:*<value>*,*<rule>*:*<value>*,etc.  For example, to set
    the line length for the LineTooLong rule you can use '-o configure
    LineTooLong:80'. If a rule is configurable, it will show the
    configuration options in the documentation for that rule

    The filename will be printed once before any errors or warnings
    for that file. The filename is preceeded by `+`

    Example Output::

        + example.robot
        W: 2, 0: No suite documentation (RequireSuiteDocumentation)
        E: 30, 0: No testcase documentation (RequireTestDocumentation)

    To see a list of all configured rules, set the 'list' option to True:

        cci task run robot_lint -o list True

    """

    task_options = {
        "configure": {
            "description": "List of rule configuration values, in the form of rule:args.",
            "default": None,
        },
        "ignore": {
            "description": "List of rules to ignore. Use 'all' to ignore all rules",
            "default": None,
        },
        "error": {
            "description": "List of rules to treat as errors. Use 'all' to affect all rules.",
            "default": None,
        },
        "warning": {
            "description": "List of rules to treat as warnings. Use 'all' to affect all rules.",
            "default": None,
        },
        "list": {
            "description": "If option is True, print a list of known rules instead of processing files.",
            "default": None,
        },
        "path": {
            "description": "The path to one or more files or folders. "
            "If the path includes wildcard characters, they will be expanded. "
            "If not provided, the default will be to process all files "
            "under robot/<project name>",
            "required": False,
        },
    }

    def _validate_options(self):
        super(RobotLint, self)._validate_options()
        self.options["list"] = process_bool_arg(self.options.get("list", False))

        self.options["path"] = process_list_arg(self.options.get("path", None))
        self.options["ignore"] = process_list_arg(self.options.get("ignore", []))
        self.options["warning"] = process_list_arg(self.options.get("warning", []))
        self.options["error"] = process_list_arg(self.options.get("error", []))
        self.options["configure"] = process_list_arg(self.options.get("configure", []))

        if self.options["path"] is None:
            self.options["path"] = [
                "robot/{}".format(self.project_config.project["name"])
            ]

    def _run_task(self):
        linter = CustomRfLint(task=self)
        result = 0

        if self.options["list"]:
            args = self._get_args()
            linter.run(args + ["--list"])

        else:
            files = self._get_files()
            args = self._get_args()

            # the result is a count of the number of errors,
            # though I don't think the caller cares.
            result = linter.run(args + sorted(files))

        # result is the number of errors detected
        if result > 0:
            message = (
                "1 error was detected"
                if result == 1
                else "{} errors were detected".format(result)
            )
            raise CumulusCIFailure(message)

    def _get_files(self):
        """Returns the working set of files to be processed"""
        expanded_paths = set()
        for path in self.options["path"]:
            expanded_paths.update(glob.glob(path))

        all_files = set()
        for path in expanded_paths:
            if os.path.isdir(path):
                for root, dirs, files in os.walk(path):
                    for filename in files:
                        if filename.endswith(".robot") or filename.endswith(
                            ".resource"
                        ):
                            all_files.add(os.path.join(root, filename))
            else:
                all_files.add(path)
        return all_files

    def _get_args(self):
        """Return rflint-style args based on the task options"""

        here = Path(__file__).parent
        args = ["--argumentfile", str((here / "lint_defaults.txt").resolve())]

        for rule in self.options["ignore"]:
            args.extend(["--ignore", rule])
        for rule in self.options["warning"]:
            args.extend(["--warning", rule])
        for rule in self.options["error"]:
            args.extend(["--error", rule])
        for config in self.options["configure"]:
            args.extend(["--configure", config])
        return args


# A better solution might be to modify rflint so we can pass in a
# function it can use to write the message. We'll save that for a
# later day. This works fine, though I grudgingly had to steal a
# little of its internal logic to keep track of the filename.
class CustomRfLint(rflint.RfLint):
    """Wrapper around RfLint to support using the task logger"""

    def __init__(self, task):
        rflint.RfLint.__init__(self)
        self.task = task

    def list_rules(self):
        """Print a list of all rules"""
        # note: rflint supports terse and verbose output. I don't
        # think the terse output is very useful, so this will always
        # print all of the documentation.
        for rule in sorted(self.all_rules, key=lambda rule: rule.name):
            self.task.logger.info("")
            self.task.logger.info(rule)
            for line in rule.doc.split("\n"):
                self.task.logger.info("    " + line)

    def report(self, linenumber, filename, severity, message, rulename, char):
        if self._print_filename is not None:
            # we print the filename only once. self._print_filename
            # will get reset each time a new file is processed.
            self.task.logger.info("+ " + self._print_filename)
            self._print_filename = None

        if severity in (rflint.WARNING, rflint.ERROR):
            self.counts[severity] += 1
            logger = (
                self.task.logger.warn
                if severity == rflint.WARNING
                else self.task.logger.error
            )
        else:
            self.counts["other"] += 1
            logger = self.task.logger.error

        logger(
            self.args.format.format(
                linenumber=linenumber,
                filename=filename,
                severity=severity,
                message=message,
                rulename=rulename,
                char=char,
            )
        )
