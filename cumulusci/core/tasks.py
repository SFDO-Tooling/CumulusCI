""" Tasks are the basic unit of execution in CumulusCI.

Subclass BaseTask or a descendant to define custom task logic
"""
import contextlib
import logging
import os
import re
import threading
import time
from contextlib import nullcontext
from typing import Any, Callable, Dict, List, Optional

from cumulusci import __version__
from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.debug import DebugMode, get_debug_mode
from cumulusci.core.exceptions import (
    ServiceNotConfigured,
    ServiceNotValid,
    TaskOptionsError,
    TaskRequiresSalesforceOrg,
)
from cumulusci.core.flowrunner import FlowCoordinator, StepSpec, StepVersion
from cumulusci.utils import cd
from cumulusci.utils.logging import redirect_output_to_logger

CURRENT_TASK = threading.local()

PROJECT_CONFIG_RE = re.compile(r"\$project_config.(\w+)")
CAPTURE_TASK_OUTPUT = os.environ.get("CAPTURE_TASK_OUTPUT")


@contextlib.contextmanager
def stacked_task(task):
    if not hasattr(CURRENT_TASK, "stack"):
        CURRENT_TASK.stack = []
    CURRENT_TASK.stack.append(task)
    try:
        yield
    finally:
        CURRENT_TASK.stack.pop()


class BaseTask:
    """BaseTask provides the core execution logic for a Task

    Subclass BaseTask and provide a `_run_task()` method with your
    code.
    """

    task_docs: str = ""
    task_options: dict = {}
    salesforce_task: bool = False  # Does this task require a salesforce org?
    name: Optional[str]
    stepnum: Optional[StepVersion]
    result: Any
    return_values: dict
    debug_mode: DebugMode
    logger: logging.Logger
    options: dict

    poll_complete: bool
    poll_count: int
    poll_interval_level: int
    poll_interval_s: int

    def __init__(
        self,
        project_config: BaseProjectConfig,
        task_config: TaskConfig,
        org_config: Optional[OrgConfig] = None,
        flow: Optional[FlowCoordinator] = None,
        name: Optional[str] = None,
        stepnum: Optional[StepVersion] = None,
        logger: Optional[logging.Logger] = None,
        **kwargs,
    ):
        self.project_config = project_config
        self.task_config = task_config
        self.org_config = org_config

        self._reset_poll()

        # dict of return_values that can be used by task callers
        self.return_values = {}
        # simple result object for introspection, often a return_code
        self.result = None
        # the flow for this task execution
        self.flow = flow
        # the task's name in the flow
        self.name = name
        # the task's stepnumber in the flow
        self.stepnum = stepnum

        self.debug_mode = get_debug_mode()
        if logger:
            self.logger = logger
        else:
            self._init_logger()

        self._init_options(kwargs)
        self._validate_options()

    def _init_logger(self):
        """Initializes self.logger"""
        if self.flow:
            self.logger = self.flow.logger.getChild(self.__class__.__name__)
        else:
            self.logger = logging.getLogger(__name__)

    def _init_options(self, kwargs):
        """Initializes self.options"""
        if self.task_config.options is None:
            self.options = {}
        else:
            self.options = self.task_config.options.copy()

        if kwargs:
            self.options.update(kwargs)

        # Handle dynamic lookup of project_config values via $project_config.attr
        for option, value in self.options.items():
            if isinstance(value, str):
                value = PROJECT_CONFIG_RE.sub(
                    lambda match: str(self.project_config.lookup(match.group(1), None)),
                    value,
                )
                self.options[option] = value

    def _validate_options(self):
        missing_required = []
        for name, config in list(self.task_options.items()):
            if config.get("required") is True and name not in self.options:
                missing_required.append(name)

        if missing_required:
            required_opts = ",".join(missing_required)
            raise TaskOptionsError(
                f"{self.__class__.__name__} requires the options ({required_opts}) and no values were provided"
            )

    def _update_credentials(self):
        """Override to do any logic to refresh credentials"""
        pass

    def _init_task(self):
        """Override to implement dynamic logic for initializing the task."""
        pass

    def __call__(self) -> dict:
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
            path = self.project_config.repo_root if self.project_config else None
            with cd(path):
                with (
                    redirect_output_to_logger(self.logger)
                    if CAPTURE_TASK_OUTPUT
                    else nullcontext()
                ):
                    self._log_begin()
                    self.result = self._run_task()
                    return self.return_values

    def _run_task(self) -> Any:
        """Subclasses should override to provide their implementation"""
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _log_begin(self):
        """Log the beginning of the task execution"""
        self.logger.info(f"Beginning task: {self.__class__.__name__}")
        if self.salesforce_task and not self.flow:
            self.logger.info(f"As user: {self.org_config.username}")
            self.logger.info(f"In org: {self.org_config.org_id}")
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
                        f"Sleeping for {self.options['retry_interval']} seconds before retry..."
                    )
                    time.sleep(self.options["retry_interval"])
                    if self.options["retry_interval_add"]:
                        self.options["retry_interval"] += self.options[
                            "retry_interval_add"
                        ]
                self.options["retries"] -= 1
                self.logger.warning(
                    f"Retrying ({self.options['retries']} attempts remaining)"
                )

    def _try(self):
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _is_retry_valid(self, e: Exception) -> bool:
        return True

    def _reset_poll(self):
        self.poll_complete = False
        self.poll_count = 0
        self.poll_interval_level = 0
        self.poll_interval_s = 1

    def _poll(self):
        """poll for a result in a loop"""
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
        """update the polling interval to be used next iteration"""
        # Increase by 1 second every 3 polls
        if self.poll_count // 3 > self.poll_interval_level:
            self.poll_interval_level += 1
            self.poll_interval_s += 1
            self.logger.info(
                "Increased polling interval to %d seconds", self.poll_interval_s
            )

    def freeze(self, step: StepSpec) -> List[dict]:
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
            return f"CumulusCI/{__version__}"

    def _run_task(self):
        raise NotImplementedError("Subclasses should provide their own implementation")

    def _update_credentials(self):
        with self.org_config.save_if_changed():
            self.org_config.refresh_oauth_token(self.project_config.keychain)

    def _validate_and_inject_namespace_prefixes(
        self,
        should_inject_namespaces: bool,
        sobjects_to_validate: List[str],
        operation_to_validate: str,
    ) -> List[str]:
        """Perform namespace injection and ensure that we can successfully access all of the selected objects."""

        global_describe = {
            entry["name"]: entry
            for entry in self.org_config.salesforce_client.describe()["sobjects"]
        }

        # Namespace injection
        if should_inject_namespaces and self.project_config.project__package__namespace:

            def inject(element: str):
                return f"{self.project_config.project__package__namespace}__{element}"

            sobjects = [
                self.fixup_sobject_name(inject, sobject, global_describe)
                for sobject in sobjects_to_validate
            ]
        else:
            sobjects = sobjects_to_validate

        # Validate CRUD
        non_accessible_objects = [
            s
            for s in sobjects
            if not (s in global_describe and global_describe[s][operation_to_validate])
        ]
        if non_accessible_objects:
            raise TaskOptionsError(
                f"The objects {', '.join(non_accessible_objects)} are not present or not {operation_to_validate}."
            )
        return sobjects

    def fixup_sobject_name(
        self,
        injection_func: Callable[[str], str],
        sobject: str,
        global_describe: Dict[str, dict],
    ) -> str:
        def _is_injectable(element: str) -> bool:
            return element.count("__") == 1

        if not _is_injectable(sobject):
            return sobject

        injected = injection_func(sobject)
        if sobject in global_describe and injected in global_describe:
            self.logger.warning(
                f"Both {sobject} and {injected} are present in the target org. Using {sobject}."
            )

        if sobject not in global_describe and injected in global_describe:
            return injected
        else:
            return sobject
