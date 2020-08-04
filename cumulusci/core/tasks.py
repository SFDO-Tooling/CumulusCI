""" Tasks are the basic unit of execution in CumulusCI.

Subclass BaseTask or a descendant to define custom task logic
"""
import contextlib
import logging
import os
import re
import time
import threading

from cumulusci import __version__
from cumulusci.utils import cd
from cumulusci.core.exceptions import ServiceNotValid, ServiceNotConfigured
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.exceptions import TaskOptionsError

CURRENT_TASK = threading.local()
CURRENT_TASK.stack = []

PROJECT_CONFIG_RE = re.compile(r"\$project_config.(\w+)")


@contextlib.contextmanager
def stacked_task(task):
    CURRENT_TASK.stack.append(task)
    try:
        yield
    finally:
        CURRENT_TASK.stack.pop()


class BaseTask(object):
    """ BaseTask provides the core execution logic for a Task

    Subclass BaseTask and provide a `_run_task()` method with your
    code.
    """

    task_docs = ""
    task_options = {}
    salesforce_task = False  # Does this task require a salesforce org?

    def __init__(
        self,
        project_config,
        task_config,
        org_config=None,
        flow=None,
        name=None,
        stepnum=None,
        **kwargs
    ):
        self.project_config = project_config
        self.task_config = task_config
        self.org_config = org_config
        self.poll_count = 0
        self.poll_interval_level = 0
        self.poll_interval_s = 1
        self.poll_complete = False

        # dict of return_values that can be used by task callers
        self.return_values = {}

        # simple result object for introspection, often a return_code
        self.result = None

        # the flow for this task execution
        self.flow = flow

        # the tasks name in the flow
        self.name = name

        # the tasks stepnumber in the flow
        self.stepnum = stepnum

        self._init_logger()
        self._init_options(kwargs)
        self._validate_options()

    def _init_logger(self):
        """ Initializes self.logger """
        if self.flow:
            self.logger = self.flow.logger.getChild(self.__class__.__name__)
        else:
            self.logger = logging.getLogger(__name__)

    def _init_options(self, kwargs):
        """ Initializes self.options """
        self.options = self.task_config.options
        if self.options is None:
            self.options = {}
        if kwargs:
            self.options.update(kwargs)

        # Handle dynamic lookup of project_config values via $project_config.attr
        for option, value in self.options.items():
            if isinstance(value, str):
                value = PROJECT_CONFIG_RE.sub(
                    lambda match: getattr(self.project_config, match.group(1), None),
                    value,
                )
                self.options[option] = value

    def _validate_options(self):
        missing_required = []
        for name, config in list(self.task_options.items()):
            if config.get("required") is True and name not in self.options:
                missing_required.append(name)

        if missing_required:
            raise TaskOptionsError(
                "{} requires the options ({}) "
                "and no values were provided".format(
                    self.__class__.__name__, ", ".join(missing_required)
                )
            )

    def _update_credentials(self):
        """ Override to do any logic to refresh credentials """
        pass

    def _init_task(self):
        """ Override to implement dynamic logic for initializing the task. """
        pass

    def __call__(self):
        if self.salesforce_task and not self.org_config:
            raise TaskRequiresSalesforceOrg(
                "This task requires a salesforce org. "
                "Use org default <name> to set a default org "
                "or pass the org name with the --org option"
            )
        self._update_credentials()
        self._init_task()

        with stacked_task(self):
            self.working_path = os.getcwd()
            with cd(self.project_config.repo_root):
                self._log_begin()
                self.result = self._run_task()
                return self.return_values

    def _run_task(self):
        """ Subclasses should override to provide their implementation """
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _log_begin(self):
        """ Log the beginning of the task execution """
        self.logger.info("Beginning task: %s", self.__class__.__name__)
        if self.salesforce_task and not self.flow:
            self.logger.info("%15s %s", "As user:", self.org_config.username)
            self.logger.info("%15s %s", "In org:", self.org_config.org_id)
        self.logger.info("")

    def _retry(self):
        while True:
            try:
                self._try()
                break
            except Exception as e:
                if not (self.options["retries"] and self._is_retry_valid(e)):
                    raise
                if self.options["retry_interval"]:
                    self.logger.warning(
                        "Sleeping for {} seconds before retry...".format(
                            self.options["retry_interval"]
                        )
                    )
                    time.sleep(self.options["retry_interval"])
                    if self.options["retry_interval_add"]:
                        self.options["retry_interval"] += self.options[
                            "retry_interval_add"
                        ]
                self.options["retries"] -= 1
                self.logger.warning(
                    "Retrying ({} attempts remaining)".format(self.options["retries"])
                )

    def _try(self):
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _is_retry_valid(self, e):
        return True

    def _poll(self):
        """ poll for a result in a loop """
        while True:
            self.poll_count += 1
            self._poll_action()
            if self.poll_complete:
                break
            time.sleep(self.poll_interval_s)
            self._poll_update_interval()

    def _poll_action(self):
        """
        Poll something and process the response.
        Set `self.poll_complete = True` to break polling loop.
        """
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _poll_update_interval(self):
        """ update the polling interval to be used next iteration """
        # Increase by 1 second every 3 polls
        if self.poll_count // 3 > self.poll_interval_level:
            self.poll_interval_level += 1
            self.poll_interval_s += 1
            self.logger.info(
                "Increased polling interval to %d seconds", self.poll_interval_s
            )

    def freeze(self, step):
        ui_step = {
            "name": self.task_config.name or self.name,
            "kind": "other",
            "is_required": True,
        }
        ui_step.update(self.task_config.config.get("ui_options", {}))
        task_config = {"options": self.options, "checks": self.task_config.checks or []}
        ui_step.update(
            {
                "path": step.path,
                "step_num": str(step.step_num),
                "task_class": self.task_config.class_path,
                "task_config": task_config,
                "source": step.project_config.source.frozenspec,
            }
        )
        return [ui_step]


class BaseSalesforceTask(BaseTask):
    """Base for tasks that need a Salesforce org"""

    name = "BaseSalesforceTask"
    salesforce_task = True

    def _get_client_name(self):
        try:
            app = self.project_config.keychain.get_service("connectedapp")
            return app.client_id
        except (ServiceNotValid, ServiceNotConfigured):
            return "CumulusCI/{}".format(__version__)

    def _run_task(self):
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _update_credentials(self):
        with self.org_config.save_if_changed():
            self.org_config.refresh_oauth_token(self.project_config.keychain)
