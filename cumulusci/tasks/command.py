""" Tasks for running a command in a subprocess

Command - run a command with optional environment variables
SalesforceCommand - run a command with credentials passed
SalesforceBrowserTest - a task designed to wrap browser testing that could run locally or remotely
"""

import json
import os
import sys

import sarge

from cumulusci.core.exceptions import CommandException
from cumulusci.core.exceptions import BrowserTestFailure
from cumulusci.core.tasks import BaseTask
from cumulusci.core.utils import process_bool_arg


class Command(BaseTask):
    """ Execute a shell command in a subprocess """

    task_docs = """
        **Example Command-line Usage:**
        ``cci task run command -o command "echo 'Hello command task!'"``

        **Example Task to Run Command:**

        ..code-block:: yaml

            hello_world:
                description: Says hello world
                class_path: cumulusci.tasks.command.Command
                options:
                command: echo 'Hello World!'
    """

    task_options = {
        "command": {"description": "The command to execute", "required": True},
        "dir": {
            "description": "If provided, the directory where the command "
            "should be run from."
        },
        "env": {
            "description": "Environment variables to set for command. Must "
            "be flat dict, either as python dict from YAML or "
            "as JSON string."
        },
        "pass_env": {
            "description": "If False, the current environment variables "
            "will not be passed to the child process. "
            "Defaults to True",
            "required": True,
        },
        "interactive": {
            "description": "If True, the command will use stderr, stdout, "
            "and stdin of the main process."
            "Defaults to False."
        },
    }

    def _init_options(self, kwargs):
        super(Command, self)._init_options(kwargs)
        if "pass_env" not in self.options:
            self.options["pass_env"] = True
        if "dir" not in self.options or not self.options["dir"]:
            self.options["dir"] = "."
        if "interactive" not in self.options:
            self.options["interactive"] = False
        if "env" not in self.options:
            self.options["env"] = {}
        else:
            try:
                self.options["env"] = json.loads(self.options["env"])
            except TypeError:
                # assume env is already dict
                pass

    def _run_task(self):
        env = self._get_env()
        self._run_command(env)

    def _get_env(self):
        if process_bool_arg(self.options["pass_env"]):
            env = os.environ.copy()
        else:
            env = {}

        env.update(self.options["env"])
        return env

    def _process_output(self, line):
        self.logger.info(line.decode("utf-8").rstrip())

    def _handle_returncode(self, returncode, stderr):
        if returncode:
            message = "Return code: {}".format(returncode)
            if stderr:
                message += "\nstderr: {}".format(stderr.read().decode("utf-8"))
            self.logger.error(message)
            raise CommandException(message)

    def _run_command(
        self, env, command=None, output_handler=None, return_code_handler=None
    ):
        if not command:
            command = self.options["command"]

        interactive_mode = process_bool_arg(self.options["interactive"])

        self.logger.info("Running command: %s", command)

        p = sarge.Command(
            command,
            stdout=sys.stdout if interactive_mode else sarge.Capture(buffer_size=-1),
            stderr=sys.stderr if interactive_mode else sarge.Capture(buffer_size=-1),
            shell=True,
            env=env,
            cwd=self.options.get("dir"),
        )
        if interactive_mode:
            p.run(input=sys.stdin)
        else:
            p.run(async_=True)
            # Handle output lines
            if not output_handler:
                output_handler = self._process_output
            while True:
                line = p.stdout.readline(timeout=1.0)
                if line:
                    output_handler(line)
                elif p.poll() is not None:
                    break
            p.wait()

        # Handle return code
        if not return_code_handler:
            return_code_handler = self._handle_returncode
        return_code_handler(p.returncode, None if interactive_mode else p.stderr)


class SalesforceCommand(Command):
    """ Execute a Command with SF credentials provided on the environment.

    Provides:
     * SF_INSTANCE_URL
     * SF_ACCESS_TOKEN
    """

    salesforce_task = True

    def _update_credentials(self):
        self.org_config.refresh_oauth_token(self.project_config.keychain)

    def _get_env(self):
        env = super(SalesforceCommand, self)._get_env()
        env["SF_ACCESS_TOKEN"] = self.org_config.access_token
        env["SF_INSTANCE_URL"] = self.org_config.instance_url
        return env


task_options = Command.task_options.copy()
task_options["extra"] = {
    "description": "If provided, will be appended to the end of the "
    "command.  Use to pass extra args to the command.",
    "required": False,
}
task_options["use_saucelabs"] = {
    "description": "If True, use SauceLabs to run the tests. The "
    "SauceLabs credentials will be fetched from the "
    "saucelabs service in the keychain and passed as "
    "environment variables to the command.  Defaults to "
    "False to run tests in the local browser.",
    "required": True,
}


class SalesforceBrowserTest(SalesforceCommand):
    """ Execute a Browser Test command locally or on SauceLabs """

    task_options = task_options

    def _init_options(self, kwargs):
        super(SalesforceBrowserTest, self)._init_options(kwargs)
        if (
            "use_saucelabs" not in self.options
            or self.options["use_saucelabs"] == "False"
        ):
            self.options["use_saucelabs"] = False

        if "extra" in self.options and self.options["extra"]:
            self.options["command"] = "{command} {extra}".format(**self.options)

    def _get_env(self):
        env = super(SalesforceBrowserTest, self)._get_env()
        if self.options["use_saucelabs"]:
            saucelabs = self.project_config.keychain.get_service("saucelabs")
            env["SAUCE_NAME"] = saucelabs.username
            env["SAUCE_KEY"] = saucelabs.api_key
            env["RUN_ON_SAUCE"] = "True"
        else:
            env["RUN_LOCAL"] = "True"
        return env

    def _handle_returncode(self, returncode, stderr):
        if returncode == 1:
            message = "Return code: {}\nstderr: {}".format(returncode, stderr)
            raise BrowserTestFailure(message)
        elif returncode:
            super(SalesforceBrowserTest, self)._handle_returncode(returncode, stderr)
