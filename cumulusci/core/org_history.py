import hashlib
import json
from datetime import datetime
from enum import Enum
from rich.text import Text
from typing import Any, Dict, List, Optional, Union
from typing_extensions import Literal
from pydantic import BaseModel, Field, root_validator
from cumulusci.core.exceptions import (
    OrgActionNotFound,
    TaskImportError,
    FlowConfigError,
)
from cumulusci.utils.hashing import hash_obj
from cumulusci.utils.options import FilePath, DirectoryPath
from cumulusci.utils.yaml.cumulusci_yml import ScratchOrg


class OrgActionStatus(Enum):
    """Enum for the status of an org history action"""

    SUCCESS = "success"
    FAILURE = "failure"
    ERROR = "error"


class ActionFileReference(BaseModel):
    """Model for tracking task that references to files in the repo"""

    path: FilePath = Field(
        ...,
        description="The state of the metadata before the task ran",
    )
    hash: str = Field(
        ...,
        description="The hash of the file's contents",
    )

    @root_validator(pre=True)
    def populate_hash(cls, values):
        path = values.get("path")
        if path:
            values["hash"] = hash_file(path)
        return values


class ActionScratchDefReference(ActionFileReference):
    """Model for tracking task that references to scratch org definitions in the repo"""

    scratchdef: Dict[str, Any] = Field(
        ...,
        description="The scratch org definition used to create the org",
    )

    @root_validator(pre=True)
    def populate_hash(cls, values):
        path = values.get("path")
        if path:
            try:
                with open(path, "r") as file:
                    values["scratchdef"] = json.load(file)
            except Exception as e:
                raise ValueError(
                    f"Error loading scratchdef from {scratch_config.config_file}: {e}"
                )
            values["hash"] = hash_obj(values["scratchdef"])
        return values

    def _load_scratchdef(self):
        self.scratchdef = self.scratch_config.config


class ActionDirectoryReference(BaseModel):
    """Model for tracking task that references to directories in the repo"""

    path: DirectoryPath = Field(
        ...,
        description="The path of the directory in the repo referenced by the task",
    )
    hash: str = Field(
        ...,
        description="The hash of the directory contents",
    )
    option: Optional[str] = Field(
        None,
        description="The option used to pass the directory to the task",
    )

    @root_validator(pre=True)
    def populate_hash(cls, values):
        path = values.get("path")
        if path:
            values["hash"] = hash_directory(path)
        return values


class ActionCommandExecution(BaseModel):
    """Model for tracking task command execution"""

    command: str = Field(
        ...,
        description="The command that was executed",
    )
    hash: str = Field(
        ...,
        description="The hash of the command",
    )
    return_code: int = Field(
        ...,
        description="The return code of the command",
    )
    output: str = Field(
        ...,
        description="The output of the command",
    )
    stderr: str = Field(
        ...,
        description="The stderr output of the command",
    )

    @root_validator(pre=True)
    def populate_hash(cls, values):
        command = values.get("command")
        if command:
            values["hash"] = hash_obj(command)
        return values


class ActionMetadataDeployment(ActionDirectoryReference):
    """Model for tracking task metadata deployment"""

    pass


class BaseOrgAction(BaseModel):
    """Base class for tracking actions run against an org"""

    timestamp: float = Field(
        default_factory=lambda: datetime.now().timestamp(),
        description="The timestamp the action was run",
    )
    repo: Optional[str] = Field(
        None,
        description="The name of the repository the action was run against",
    )
    branch: Optional[str] = Field(
        None,
        description="The name of the branch the action was run against",
    )
    commit: Optional[str] = Field(
        None,
        description="The commit SHA the action was run against",
    )

    class Config:
        use_enum_values = True


class BaseOrgActionResult(BaseOrgAction):
    hash_action: Optional[str] = Field(
        None,
        description="A unique hash for the action instance",
    )
    hash_config: Optional[str] = Field(
        None,
        description="A unique hash representing the action instance's configuration",
    )
    duration: float = Field(
        ...,
        description="The duration of the action",
    )
    status: OrgActionStatus = Field(
        ...,
        description="The status of the action",
    )
    log: str = Field(
        ...,
        description="The log output of the action",
    )
    exception: Optional[str] = Field(
        None,
        description="The exception message if the action failed",
    )

    @root_validator(pre=True)
    def populate_duration(cls, values):
        duration = values.get("duration")
        if not duration:
            timestamp = values.get("timestamp")
            if timestamp:
                values["duration"] = datetime.now().timestamp() - timestamp
        return values

    def get_config_hash_data(self):
        data = {
            "action_type": self.action_type,
        }
        return data

    def calculate_action_hash(self):
        """A unique hash for the action instance"""
        hash_data = self.dict()
        return hash_obj(hash_data)

    def calculate_config_hash(self):
        """A unique hash representing the action's non-instance specific configuration"""
        hash_data = self.get_config_hash_data()
        hashed = hash_obj(hash_data)
        return hashed

    @property
    def column_hash(self):
        return f"Action:\n[bold]{self.hash_action}[/bold]\n\nConfig:\n[bold]{self.hash_config}[/bold]"

    @property
    def column_date(self):
        date = datetime.fromtimestamp(self.timestamp)
        data = []
        data.append(date.strftime("%Y-%m-%d"))
        data.append(date.strftime("%H:%M:%S"))
        data.append(f"{self.duration:.2f}s")
        return "\n".join(data)

    @property
    def column_type(self):
        if hasattr(self, "action_type"):
            return self.action_type
        return self.__class__.__name__.replace("OrgAction", "").replace("Action", "")

    @property
    def column_status(self):
        status_colors = {
            "success": "green",
            "failure": "orange",
            "error": "red",
        }
        color = status_colors.get(self.status, "white")
        return Text(str(self.status), style=color)

    @property
    def column_details(self):
        if self.status == OrgActionStatus.SUCCESS.value:
            return "\n".join(self.log.split("\n")[:-3])
        if self.status == OrgActionStatus.FAILURE.value:
            return self.exception
        if self.status == OrgActionStatus.ERROR.value:
            return self.exception


class SFCLIOrgActionMixin(BaseModel):
    sf_command: ActionCommandExecution = Field(
        ...,
        description="The Salesforce CLI command used to create the org",
    )

    def get_config_hash_data(self):
        data = super().get_config_hash_data()
        data.update(self.sf_command.command)
        return data

    @property
    def log(self):
        log = []
        log.append(self.sf_command.output)
        log.append(self.sf_command.stderr)
        return "\n".join(log)


class OrgCreateAction(BaseOrgActionResult, SFCLIOrgActionMixin):
    """Model for tracking org creations"""

    action_type: Literal["OrgCreate"] = Field()
    days: int = Field(
        ...,
        description="The number of days the org is configured to live",
        max=30,
        min=1,
    )
    namespaced: bool = Field(
        ...,
        description="Whether the org is namespaced",
    )
    scratch_org: ScratchOrg = Field(
        ...,
        description="The scratch org configuration from cumulusci.yml's orgs -> scratch section.",
    )
    config: Optional[ActionScratchDefReference] = Field(
        None,
        description="The scratch org definition used to create the org",
    )
    org_id: Optional[str] = Field(
        None,
        description="The Salesforce org ID",
    )
    username: Optional[str] = Field(
        None,
        description="The username of the org",
    )
    devhub: Optional[str] = Field(
        None,
        description="The username of the Dev Hub org",
    )
    sfdx_alias: Optional[str] = Field(
        None,
        description="The alias of the org in the SF CLI keychain",
    )
    login_url: Optional[str] = Field(
        None,
        description="The instance URL of the org",
    )
    instance: Optional[str] = Field(
        None,
        description="The instance of the org",
    )

    def get_config_hash_data(self):
        data = super().get_config_hash_data()
        data["config"] = self.config.hash
        data["namespaced"] = self.namespaced
        return data

    @property
    def column_details(self):
        if self.status == OrgActionStatus.SUCCESS.value:
            details = []
            details.append(f"SF CLI Alias:  {self.sfdx_alias}")
            details.append(f"Org ID:        {self.org_id}")
            details.append(f"Username:      {self.username}")
            # details.append(f"Dev Hub:       {self.devhub}")
            # details.append(f"Instance:      {self.instance}")
            # details.append(f"Login URL:     {self.login_url}")
            details.append(f"Days:          {self.days}")
            details.append(f"Namespaced:    {self.namespaced}")
            details.append(f"ScratchDef:    {self.config.path}")
            return "\n".join(details)
        if self.status == OrgActionStatus.FAILURE.value:
            return self.exception
        if self.status == OrgActionStatus.ERROR.value:
            return self.exception


class OrgConnectAction(BaseOrgActionResult):
    """Model for tracking org connections"""

    action_type: Literal["OrgConnect"] = Field()


class OrgDeleteAction(BaseOrgActionResult, SFCLIOrgActionMixin):
    """Model for tracking org deletions"""

    action_type: Literal["OrgDelete"] = Field()
    org_id: str = Field(
        ...,
        description="The Salesforce org ID",
    )


class OrgImportAction(BaseOrgActionResult):
    """Model for tracking org imports"""

    action_type: Literal["OrgImport"] = Field()
    sf_org_name: str = Field(
        ...,
        description="The name of the Salesforce org in the SF CLI keychain",
    )


class BaseTaskAction(BaseModel):
    """Model for tracking an actively running task run against an org
    for later reporting as an action with results
    """

    name: str = Field(
        ...,
        description="The name of the task",
    )
    description: Optional[str] = Field(
        None,
        description="The description of the task",
    )
    group: Optional[str] = Field(
        None,
        description="The group of the task",
    )
    class_path: str = Field(
        ...,
        description="The class of the task",
    )
    options: dict = Field(
        ...,
        description="The options passed to the task",
    )
    parsed_options: dict = Field(
        {},
        description="The options after being parsed by the task",
    )
    files: Optional[List[ActionFileReference]] = Field(
        [],
        description="The file references of the task",
    )
    directories: Optional[List[ActionDirectoryReference]] = Field(
        [],
        description="The directory references of the task",
    )
    commands: Optional[List[ActionCommandExecution]] = Field(
        [],
        description="The commands executed by the task",
    )
    deploys: Optional[List[ActionMetadataDeployment]] = Field(
        [],
        description="The metadata deployments executed by the task",
    )

    def get_config_hash_data(self):
        return {
            "action_type": self.action_type,
            "class_path": self.class_path,
            "parsed_options": self.parsed_options,
            "files": [f.hash for f in self.files],
            "directories": [d.hash for d in self.directories],
            "commands": [c.hash for c in self.commands],
            "deploys": [d.hash for d in self.deploys],
        }

    @property
    def column_details(self):
        details = []
        details.append(f"Task: {self.name}")
        details.append(f"Class: {self.class_path}")
        details.append("Options:")
        for key, value in self.options.items():
            details.append(f"  {key}: {value}")

        if self.exception is not None and self.exception != "None":
            details.append("Exception:")
            details.append(self.exception)
        return "\n".join(details)


class TaskActionTracker(BaseTaskAction, BaseOrgAction):
    """Model for tracking a single task run against an org"""

    pass


class TaskOrgAction(BaseTaskAction, BaseOrgActionResult):
    """Model for the outcome of a single task run against an org"""

    action_type: Literal["Task"] = Field()
    return_values: dict = Field(
        ...,
        description="The return values of the task",
    )

    def get_runnable_dependencies(self, project_config):
        """Return a list of dependencies that are valid input ProjectDependencies"""

        # Handle update_dependencies task
        if self.name == "update_dependencies" and "dependencies" in self.return_values:
            dependencies = self.return_values["dependencies"]

            # Convert the dependencies to the format expected by the task
            formatted_dependencies = []
            for dep in dependencies:
                if "namespace" in dep:
                    formatted_dep = {
                        "namespace": dep["namespace"],
                        "version": dep["version"],
                    }
                elif "github" in dep:
                    formatted_dep = {
                        "github": dep["github"],
                        "subfolder": dep.get("subfolder"),
                        "ref": dep.get("ref"),
                        "unmanaged": dep.get("unmanaged", False),
                        "namespace_inject": dep.get("namespace_inject"),
                    }
                    formatted_dep = {
                        k: v for k, v in formatted_dep.items() if v is not None
                    }
                else:
                    # Handle other types of dependencies if necessary
                    formatted_dep = dep

                formatted_dependencies.append(formatted_dep)

            return formatted_dependencies


class BaseFlowAction(BaseModel):
    name: str = Field(
        ...,
        description="The name of the flow",
    )
    description: Optional[str] = Field(
        None,
        description="The description of the flow",
    )

    group: Optional[str] = Field(
        None,
        description="The group of the flow",
    )
    config_steps: dict = Field(
        ...,
        description="The flow configuration",
    )

    def get_config_hash_data(self):
        return {
            "action_type": self.action_type,
            "config_steps": self.config_steps,
        }

    def _get_details(self):
        details = []
        details.append(f"Flow: {self.name}")
        if self.group is not None and self.group != "None":
            details.append(f"Group: {self.group}")
        if self.config_steps and len(self.config_steps) > 0:
            details.append("Config:")
            for key, value in self.config_steps.items():
                details.append(f"  {key}: {value}")
        return details

    @property
    def column_details(self):
        return "\n".join(self._get_details())


class FlowActionStepTracker(BaseModel):
    task: TaskActionTracker = Field(
        ...,
        description="The initialized task tracker for the step",
    )
    when: Optional[str] = Field(
        None,
        description="The condition for the step to run",
    )


class FlowActionStep(BaseModel):
    task: TaskOrgAction = Field(
        ...,
        description="The initialized task tracker for the step",
    )


class FlowActionTracker(BaseFlowAction, BaseOrgAction):
    """Model for tracking a flow run against an org"""

    steps: List[FlowActionStepTracker] = Field(
        ...,
        description="The initialized step trackers for each flow step",
    )


class FlowOrgAction(BaseFlowAction, BaseOrgActionResult):
    """Model for the outcome of a flow run against an org"""

    action_type: Literal["Flow"] = Field()
    steps: List[FlowActionStep] = Field(
        ...,
        description="The details and results from all steps in the flow",
    )

    def get_config_hash_data(self):
        return {
            "action_type": self.action_type,
            "config_steps": self.config_steps,
            "steps": [step.task.hash_config for step in self.steps],
        }

    @property
    def log(self):
        log = []
        log.append(f"Flow: {self.name}")
        if self.group is not None and self.group != "None":
            log.append(f"Group: {self.group}")
        log.append(f"Status: {self.status}")
        log.append(f"Duration: {self.duration}")
        log.append("Details:")
        log.extend(self._get_details())
        return "\n".join(log)

    def _get_details(self):
        details = super()._get_details()
        if self.exception is not None and self.exception != "None":
            details.append("Exception:")
            details.append(self.exception)
        details.append("Steps:")
        for step in self.steps:
            details.append(f"  {step.task.name}")
            details.append(f"    Status: {step.task.status}")
            details.append(f"    Duration: {step.task.duration}")
        return details


OrgActionType = Union[
    OrgConnectAction,
    OrgImportAction,
    OrgDeleteAction,
    OrgCreateAction,
    TaskOrgAction,
    FlowOrgAction,
]


def actions_from_dict(data: dict) -> List[OrgActionType]:
    actions = []
    for action_data in data:
        action: OrgActionType | None = None
        if "action_type" not in action_data:
            raise ValueError("Missing required key 'action_type'")
        if action_data["action_type"] == "OrgConnect":
            action = OrgConnectAction(**action_data)
        elif action_data["action_type"] == "OrgImport":
            action = OrgImportAction(**action_data)
        elif action_data["action_type"] == "OrgDelete":
            action = OrgDeleteAction(**action_data)
        elif action_data["action_type"] == "OrgCreate":
            action = OrgCreateAction(**action_data)
        elif action_data["action_type"] == "Task":
            action = TaskOrgAction(**action_data)
        elif action_data["action_type"] == "Flow":
            action = FlowOrgAction(**action_data)
        else:
            raise ValueError(f"Unknown action_type: {action_data['action_type']}")
        actions.append(action)
    return actions


class OrgHistory(BaseModel):
    """Model for tracking the history of actions run against a CumulusCI org profile"""

    hash_config: Optional[str] = Field(
        None,
        description="A unique hash representing the complete configuration of the org",
    )

    actions: List[OrgActionType] = Field(
        ...,
        description="The actions run against the org",
    )

    def calculate_config_hash(self):
        hash_data = [action.hash_config for action in self.actions]
        return hash_obj(hash_data)

    @classmethod
    def parse_obj(cls, obj):
        obj = super().parse_obj(obj)

        # Calculate hashes for actions
        for action in obj.actions:
            if action.hash_action is None:
                action.hash_action = action.calculate_action_hash()
            if action.hash_config is None:
                action.hash_config = action.calculate_config_hash()

        return obj

    def filtered_actions(
        self,
        action_type: Optional[
            Literal["OrgCreate", "OrgConnect", "OrgImport", "OrgDelete", "Task", "Flow"]
        ] = None,
        status: Optional[OrgActionStatus] = None,
        action_hash: Optional[str] = None,
        config_hash: Optional[str] = None,
        exclude_action_hash: Optional[str] = None,
        exclude_config_hash: Optional[str] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[OrgActionType]:
        actions = self.actions
        if action_type:
            actions = [a for a in actions if a.action_type == action_type]
        if status:
            actions = [a for a in actions if a.status == status]
        if action_hash:
            actions = [a for a in actions if a.hash_action == action_hash]
        if config_hash:
            actions = [a for a in actions if a.hash_config == config_hash]
        if exclude_action_hash:
            actions = [a for a in actions if a.hash_action != exclude_action_hash]
        if exclude_config_hash:
            actions = [a for a in actions if a.hash_config != exclude_config_hash]
        if before:
            actions = [a for a in actions if a.hash_action < before]
        if after:
            actions = [a for a in actions if a.hash_action > after]
        return actions

    def get_action_by_hash(self, hash: str) -> OrgActionType | None:
        for action in self.actions:
            if action.hash_action == hash:
                return action
        raise OrgActionNotFound(f"Action with hash {hash} not found in org history")
