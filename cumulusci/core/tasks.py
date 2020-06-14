""" Tasks are the basic unit of execution in CumulusCI.

Subclass BaseTask or a descendant to define custom task logic
"""
import contextlib
import logging
import os
import time
import threading
from typing import Any

from cumulusci import __version__
from cumulusci.utils import cd
from cumulusci.core.exceptions import ServiceNotValid, ServiceNotConfigured
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.utils.json.resumption_file import ResumptionFile

CURRENT_TASK = threading.local()
CURRENT_TASK.stack = []


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
        **kwargs,
    ):
        assert task_config
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
        for option, value in list(self.options.items()):
            try:
                if value.startswith("$project_config."):
                    attr = value.replace("$project_config.", "", 1)
                    self.options[option] = getattr(self.project_config, attr, None)
            except AttributeError:
                pass

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
        """ Override to do any logic  to refresh credentials """
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

    def cleanup(self):
        pass

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

    def set_resumption_file(self, file):
        pass


class ResumableTask(BaseTask):
    """A task which can be resumed

    Resumable tasks have a different internal API and store
    their state at a URL location instead of only on the
    Python stack.

    Attributes of resumable tasks are persisted by default.

    __setattr__ is overriden to require you to declare values and types
    in order to encourage you to think through what should be
    persisted and what should not.

    Add transient attributes through self.set_nonpersistent_value to
    prevent them from being persisted.
    """

    options: dict = {}
    name: str = None
    logger: Any = None
    resumption_fs_resource: Any = None
    project_config: dict = None
    task_config: dict = None
    org_config: dict = None
    poll_count: int = None
    poll_interval_level: int = None
    poll_interval_s: int = None
    poll_complete: bool = None
    return_values: dict = None
    result: Any = None
    flow: Any = None
    stepnum: Any = None

    default_excluded_fields = (
        "name",
        "logger",
        "task_options",
        "project_config",
        "task_config",
        "org_config",
        "poll_count",
        "poll_interval_level",
        "poll_interval_s",
        "poll_complete",
        "return_values",
        "result",
        "flow",
        "stepnum",
        "excluded_fields",
        "working_path",
        "sf",
        "bulk",
        "tooling",
        "resuming",
    )

    def __init__(
        self,
        *args,
        resumption_fs_resource: ResumptionFile = None,
        resuming=False,
        **kwargs,
    ):
        self.__dict__["excluded_fields"] = set(self.default_excluded_fields)

        self.set_nonpersistent_value("resumption_fs_resource", resumption_fs_resource)
        self.set_nonpersistent_value("resuming", resuming)

        super().__init__(*args, **kwargs)

    def _init_options(self, kwargs):
        if self.resuming:
            self.options = self.resumption_fs_resource.state_data["options"]
        else:
            super()._init_options(kwargs)

    def _validate_options(self):
        if not self.resuming:
            super()._validate_options()

    def _run_task(self):
        self._start()
        self._run_steps()

    def _start(self):
        "Override this: Do any kind of task setup or logging that is necessary."
        self.logger.info(f"Starting task {self.__class__.name}")

    def _run_steps(self):
        "Run multiple steps until finished. Usually do not override this."
        while not self._is_finished():
            self._run_step()
            self.resumption_fs_resource.state_data = self.dict()
            self.resumption_fs_resource.save()
        self.resumption_fs_resource.cleanup()
        self._after_finished()

    def resume(self):
        "Resume this task. Usually do not need to override this."
        self._resume()
        self._run_steps()

    def set_nonpersistent_value(self, key, value):
        "Save a value to memory but not to persistent storage"
        self.__dict__[key] = value
        self.excluded_fields.add(key)

    def dict(self):
        return {k: v for k, v in self.__dict__.items() if k not in self.excluded_fields}

    def __setattr__(self, name, value):
        if name not in self.excluded_fields and not hasattr(self.__class__, name):
            raise AttributeError(f"Undeclared attribute {name}")
        self.__dict__[name] = value

    def _after_finished(self):
        "Override to to any kind of cleanup post-execution"
        pass


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
        orig_config = self.org_config.config.copy()
        self.org_config.refresh_oauth_token(self.project_config.keychain)
        if self.org_config.config != orig_config:
            self.logger.info("Org info updated, writing to keychain")
            self.project_config.keychain.set_org(self.org_config)
