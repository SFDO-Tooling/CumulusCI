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
from datetime import datetime
from io import StringIO
from typing import Any, Callable, Dict, List, Optional, Type, Union

from pydantic.error_wrappers import ValidationError

from cumulusci import __version__
from cumulusci.core.config import TaskConfig
from cumulusci.core.config.org_config import OrgConfig
from cumulusci.core.org_history import (
    ActionCommandExecution,
    ActionDirectoryReference,
    ActionFileReference,
    ActionGithubMetadataDeploy,
    ActionRepoMetadataDeploy,
    ActionPackageInstall,
    ActionPackageUpgrade,
    ActionUrlMetadataDeploy,
    OrgActionStatus,
    TaskActionTracker,
    TaskOrgAction,
)
from cumulusci.core.config.project_config import BaseProjectConfig
from cumulusci.core.debug import DebugMode, get_debug_mode
from cumulusci.core.exceptions import (
    CumulusCIFailure,
    ServiceNotConfigured,
    ServiceNotValid,
    TaskOptionsError,
    TaskRequiresSalesforceOrg,
)
from cumulusci.core.flowrunner import FlowCoordinator, StepSpec, StepVersion
from cumulusci.salesforce_api.package_install import PackageInstallOptions
from cumulusci.utils import cd
from cumulusci.utils.logging import redirect_output_to_logger
from cumulusci.utils.metaprogramming import classproperty
from cumulusci.utils.options import CCIOptions, ReadOnlyOptions

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
    Options: Optional[Type[CCIOptions]] = None
    salesforce_task: bool = False  # Does this task require a salesforce org?
    name: Optional[str]
    stepnum: Optional[StepVersion]
    result: Any
    return_values: dict
    debug_mode: DebugMode
    logger: logging.Logger
    options: dict
    tracker: TaskActionTracker
    action: TaskOrgAction | None

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
        self._track_options()

        self.action = None
        self.tracker = TaskActionTracker(
            name=self.name,
            description=self.task_config.description,
            group=self.task_config.group,
            class_path=self.task_config.class_path,
            options=self.task_config.options,
            parsed_options=(
                self.parsed_options.to_dict()
                if self.Options
                else getattr(self, "options", {})
            ),
            files=[],
            directories=[],
            commands=[],
            deploys={
                "github": [],
                "zip_url": [],
                "repo": [],
            },
            package_installs=[],
            repo=self.project_config.repo_url,
            branch=self.project_config.repo_branch,
            commit=self.project_config.repo_commit,
        )

    def _init_logger(self):
        """Initializes self.logger"""
        if self.flow:
            self.logger = self.flow.logger.getChild(self.__class__.__name__)
        else:
            self.logger = logging.getLogger(__name__)

        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        self.logger.addHandler(handler)

    @classproperty
    def task_options(cls):  # type: ignore  -- doesn't like the signature override below
        "Convert Options dict into old fashioned task_options syntax"
        if cls.Options:
            return cls.Options.as_task_options()
        else:
            return {}

    task_options: Union[classproperty, Dict]

    def _init_options(self, kwargs):
        """Initializes self.options"""
        if self.task_config.options is None:
            self.options = {}
        else:
            self.options = self.task_config.options.copy()

        if kwargs:
            self.options.update(kwargs)

        # Handle dynamic lookup of project_config values via $project_config.attr
        def process_options(option):
            if isinstance(option, str):
                return PROJECT_CONFIG_RE.sub(
                    lambda match: str(self.project_config.lookup(match.group(1), None)),
                    option,
                )
            elif isinstance(option, dict):
                processed_dict = {}
                for key, value in option.items():
                    processed_dict[key] = process_options(value)
                return processed_dict
            elif isinstance(option, list):
                processed_list = []
                for item in option:
                    processed_list.append(process_options(item))
                return processed_list
            else:
                return option

        self.options = process_options(self.options)

        if self.Options:
            try:
                specials = ["debug_before", "debug_after", "no_prompt"]
                options_without_specials = {
                    opt: val for opt, val in self.options.items() if opt not in specials
                }
                self.parsed_options = self.Options(**options_without_specials)
                self.options = ReadOnlyOptions(self.options)
            except ValidationError as e:
                try:
                    errors = [
                        f"Error in '{error['loc'][0]}' option: '{error['msg']}'"
                        for error in e.errors()
                    ]
                    plural = "s" if len(errors) > 1 else ""
                    errorstrs = ", ".join(errors)
                    message = f"Task Options Error{plural}: {errorstrs}"
                except (AttributeError, IndexError):
                    message = f"Task Options Error: {e.errors()}"
                if "extra fields not permitted" in message:
                    message = message.replace("extra fields", "extra options")
                raise TaskOptionsError(message) from e
            except (TaskOptionsError, TypeError) as e:
                raise TaskOptionsError(
                    f"Task Options Error: Error in '{self.options}' option: '{e}'"
                )

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

    def _track_options(self):
        """Override with to track actions based on the initialized task options"""
        pass

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
            try:
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
                        self._record_result()
                        return self.return_values
            except Exception as e:
                self._record_result(e)
                raise e from e

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
        task_config = {
            "options": self.options,
            "checks": self.task_config.checks or [],
        }
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

    def _track_command(
        self,
        command: str,
        return_code: int,
        output: str,
        stderr: str,
    ) -> None:
        """
        Track the execution of a command.

        Args:
            command (str): The command that was executed.
            return_code (int): The return code of the command.
            output (str): The standard output of the command.
            stderr (str): The standard error output of the command.

        Returns:
            None
        """
        self.tracker.commands.append(
            ActionCommandExecution(
                command=command,
                return_code=return_code,
                output=output,
                stderr=stderr,
            )
        )

    def _track_file_reference(self, path: str, name: str) -> None:
        """
        Track a file reference.

        Args:
            path (str): The path to the file.
            name (str): The name of the file.

        Returns:
            None
        """
        self.tracker.files.append(ActionFileReference(path=path, name=name))

    def _track_directory_reference(self, path: str, name: str) -> None:
        """
        Track a directory reference.

        Args:
            path (str): The path to the directory.
            name (str): The name of the directory.

        Returns:
            None
        """
        self.tracker.directories.append(ActionDirectoryReference(path=path, name=name))

    def _track_metadata_deploy(
        self,
        path: str,
        hash: str,
        size: int,
        option: str = None,
    ) -> None:
        """
        Track a metadata deployment.

        Args:
            path (str): The path to the metadata.
            hash (str): The hash of the deployed metadata.
            size (int): The size of the deployed metadata.
            option (str, optional): Additional options for the deployment. Defaults to None.

        Returns:
            None
        """
        self.tracker.deploys.repo.append(
            ActionRepoMetadataDeploy(
                path=path,
                hash=hash,
                size=size,
                option=option,
            )
        )

    def _track_github_metadata_deploy(
        self,
        repo: str,
        hash: str,
        size: int,
        commit: str,
        branch: str | None,
        tag: str | None,
        subfolder: str | None,
    ) -> None:
        """
        Track a GitHub metadata deployment.

        Args:
            repo (str): The repository where the metadata is stored.
            hash (str): The hash of the deployed metadata.
            size (int): The size of the deployed metadata.
            commit (str): The commit hash of the deployment.
            branch (str | None): The branch of the deployment. Defaults to None.
            tag (str | None): The tag of the deployment. Defaults to None.
            subfolder (str | None): The subfolder of the deployment. Defaults to None.

        Returns:
            None
        """
        self.tracker.deploys.github.append(
            ActionGithubMetadataDeploy(
                repo=repo,
                commit=commit,
                branch=branch,
                tag=tag,
                subfolder=subfolder,
                hash=hash,
                size=size,
            )
        )

    def _track_url_metadata_deploy(
        self,
        url: str,
        subfolder: str | None,
        hash: str,
        size: int,
    ) -> None:
        """
        Track a URL metadata deployment.

        Args:
            url (str): The URL where the metadata is stored.
            subfolder (str | None): The subfolder of the deployment. Defaults to None.
            hash (str): The hash of the deployed metadata.
            size (int): The size of the deployed metadata.

        Returns:
            None
        """
        self.tracker.deploys.url.append(
            ActionUrlMetadataDeploy(
                url=url,
                subfolder=subfolder,
                hash=hash,
                size=size,
            )
        )

    def _track_package_install(
        self,
        version_id=None,
        namespace=None,
        package_id=None,
        name=None,
        version=None,
        package_type=None,
        is_beta=None,
        is_promotable=None,
        ancestor_id=None,
        previous_version_id=None,
        previous_version=None,
        activate_remote_site_settings=None,
        name_conflict_resolution=None,
        security_type=None,
        apex_compile_type=None,
        upgrade_type=None,
    ) -> None:
        """
        Track a package installation.

        Args:
            version_id (str, optional): The version ID of the package. Defaults to None.
            namespace (str, optional): The namespace of the package. Defaults to None.
            package_id (str, optional): The package ID. Defaults to None.
            name (str, optional): The name of the package. Defaults to None.
            version (str, optional): The version of the package. Defaults to None.
            package_type (str, optional): The type of the package. Defaults to None.
            is_beta (bool, optional): Whether the package is a beta version. Defaults to None.
            is_promotable (bool, optional): Whether the package is promotable. Defaults to None.
            ancestor_id (str, optional): The ancestor ID of the package. Defaults to None.
            previous_version_id (str, optional): The previous version ID of the package. Defaults to None.
            previous_version (str, optional): The previous version of the package. Defaults to None.
            activate_remote_site_settings (bool, optional): Whether to activate remote site settings. Defaults to None.
            name_conflict_resolution (str, optional): The name conflict resolution strategy. Defaults to None.
            security_type (str, optional): The security type of the package. Defaults to None.
            apex_compile_type (str, optional): The Apex compile type. Defaults to None.
            upgrade_type (str, optional): The upgrade type of the package. Defaults to None.

        Returns:
            None
        """
        kwargs = {
            "version_id": version_id,
            "namespace": namespace,
            "package_id": package_id,
            "name": name,
            "version": version,
            "package_type": package_type,
            "is_beta": is_beta,
            "is_promotable": is_promotable,
            "ancestor_id": ancestor_id,
            # "password": password,
        }

        if hasattr(self, "install_options"):
            install_options = self.install_options
        else:
            install_options = PackageInstallOptions.from_task_options(
                {
                    "activate_remote_site_settings": activate_remote_site_settings,
                    "name_conflict_resolution": name_conflict_resolution,
                    "security_type": security_type,
                    "apex_compile_type": apex_compile_type,
                    "upgrade_type": upgrade_type,
                }
            )

        kwargs.update(install_options.dict())
        kwargs["security_type"] = kwargs["security_type"].value
        kwargs["name_conflict_resolution"] = kwargs["name_conflict_resolution"].value

        action: ActionPackageInstall | ActionPackageUpgrade | None = None
        if previous_version_id or previous_version:
            kwargs["previous_version"] = previous_version
            kwargs["previous_version_id"] = previous_version_id
            action = ActionPackageUpgrade.parse_obj(kwargs)
        else:
            action = ActionPackageInstall.parse_obj(kwargs)
        self.tracker.package_installs.append(action)

    def _record_result(self, exception=None) -> None:
        data = self.tracker.dict()
        if exception:
            if isinstance(exception, CumulusCIFailure):
                status = OrgActionStatus.FAILURE.value
            else:
                status = OrgActionStatus.ERROR.value
        else:
            status = OrgActionStatus.SUCCESS.value
        data["action_type"] = "Task"
        data["status"] = status
        data["log"] = self.logger.handlers[0].stream.getvalue()
        data["duration"] = datetime.now().timestamp() - self.tracker.timestamp
        data["exception"] = str(exception) if exception else None
        return_values = self.return_values
        if isinstance(self.return_values, str):
            return_values = {"result": self.return_values}
        data["return_values"] = return_values
        self.action = TaskOrgAction.parse_obj(data)
        self.action.hash_action = self.action.calculate_action_hash()
        self.action.hash_config = self.action.calculate_config_hash()


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


class BaseSalesforceActionTask(BaseSalesforceTask):
    """Base class for tasks that perform actions on a Salesforce org"""

    modifies_data = False
    modifies_metadata = False
    modifies_security = False
    references_directories = False
    references_files = False
    runs_commands = False
