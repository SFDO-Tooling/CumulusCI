"""
Pydantic models for validating cumulusci.yml

Note: If you change the model here, you should run `make schema`
to update the JSON Schema version in cumulusci.jsonschema.json
"""

from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import Field, root_validator, validator
from pydantic.types import DirectoryPath
from typing_extensions import Literal, TypedDict

from cumulusci.core.enums import StrEnum
from cumulusci.utils.fileutils import DataInput, load_from_source
from cumulusci.utils.yaml.model_parser import CCIDictModel, HashableBaseModel
from cumulusci.utils.yaml.safer_loader import load_yaml_data

default_logger = getLogger(__name__)


#  type aliases
PythonClassPath = str
URL = str


# additionalProperties here works around an
# incompatibility with VSCode's Red Hat YAML validator
# Can probably remove it at some future date if the
# bug/incompatibilty is fixed elsewhere in the stack
VSCodeFriendlyDict = Field({}, additionalProperties=True)


class PreflightCheckActionEnum(StrEnum):
    "The allowed values for the action field of a preflight check"
    error = "error"
    warn = "warn"
    optional = "optional"
    skip = "skip"


class PreflightCheck(CCIDictModel):
    when: str = Field(
        None,
        title="When Clause",
        description="A Jinja expression used to determine if the preflight check triggers.",
        examples=[
            "org.scratch == True",
            "'npsp' not in tasks.get_installed_packages()",
        ],
    )
    action: PreflightCheckActionEnum = Field(
        None,
        title="Action",
        description="The action to take if the preflight check when clause evaluates to True.",
        examples=["error", "warn", "optional", "skip"],
    )
    message: Optional[str] = Field(
        None,
        title="Message",
        description="The message to display if the preflight check evaluates to True.",
        examples=["The org must be a scratch org."],
    )

    class Config:
        title = "Preflight Check Definition"
        description = "A preflight check to run before a step or plan in MetaDeploy."


class StepUIOptionsKindEnum(StrEnum):
    metadata = "Metadata"
    onetime = "One Time Apex"
    managed = "Managed Package"
    data = "Data"
    other = "Other"


class StepUIOptions(TypedDict):
    name: Optional[str]  # Name of the step shown to the user.
    description: Optional[str]  # Description of the step shown to the user.
    is_required: Optional[bool]  # If True, the step will always be run.
    is_recommended: Optional[
        bool
    ]  # If True, the step will be run unless the user opts out.
    kind: Optional[
        StepUIOptionsKindEnum
    ]  # The kind of step. Used to group steps in the UI.


class Step(CCIDictModel):
    task: str = Field(
        None,
        title="Task",
        description="The name of the task to run",
        examples=["deploy", "load_custom_settings"],
    )
    flow: str = Field(
        None,
        title="Flow",
        description="The name of the flow to run",
        examples=["dependencies", "config_dev"],
    )
    ignore_failure: bool = Field(
        False,
        title="Ignore Failure",
        description="If True, ignore failures on this step and continues with the next step.",
    )
    # is this allowed?
    when: str = Field(
        None,
        title="When",
        description="A Jinja expression to determine if the step should run",
        examples=[
            "org.scratch == True",
            "'npsp' not in tasks.get_installed_packages()",
        ],
    )
    options: Dict[str, Any] = Field(
        {},
        additionalProperties=True,
        title="Options",
        description="Options for the task or flow. For flows, this should be a dictionary with a key for the task name containing keys for each option.",
        examples=[{"path": "src"}, {"deploy": {"path": "src"}}],
    )
    ui_options: StepUIOptions = Field(
        {},
        additionalProperties=True,
        title="UI Options",
        description="Options for the task or flow that are only used by MetaDeploy. For flows, this should be a dictionary with a key for the task name containing keys for each option.",
        examples=[
            {"name": "Deploy Required Config", "kind": "managed"},
            {
                "name": "Deploy Recommended Config",
                "kind": "metadata",
                "is_required": False,
                "is_recommended": True,
            },
            {
                "name": "Deploy Optional Config",
                "kind": "other",
                "is_required": False,
                "is_recommended": False,
            },
        ],
    )
    checks: List[PreflightCheck] = Field(
        [],
        title="Preflight Checks",
        description="A list of preflight checks to run before the step.",
        examples=[
            [
                {
                    "when": "org.scratch == True",
                    "action": "error",
                    "message": "The org must be a scratch org.",
                }
            ]
        ],
    )
    description: str = Field(
        None,
        title="Description",
        description="A description of the step, shown in output logs when running the flow.",
    )

    class Config:
        title = "Step Definition"
        description = "A step to run in a flow. Steps are either a task or a flow and can contain configuration options for the task or flow."

    @root_validator()
    def _check(cls, values):
        has_task = values.get("task") and values["task"] != "None"
        has_flow = values.get("flow") and values["flow"] != "None"
        assert not (
            has_task and has_flow
        ), "Steps must have either task or flow but not both"
        return values


class Task(CCIDictModel):
    class_path: str = Field(
        None,
        title="Class Path",
        description="The Python class path to the task class. CumulusCI includes the repo root in the Python path, so you can use a relative path from the repo root.",
        examples=["cumulusci.tasks.salesforce.Deploy", "tasks.my_task.MyTask"],
    )
    description: str = Field(
        None,
        title="Description",
        description="A description of the task shown via the cli in task list, task info, and when running the task directly or via a flow.",
        examples=["Deploys the post-install metadata."],
    )
    group: str = Field(
        None,
        title="Group",
        description="The group of the task, used to group tasks in cci task list.",
        examples=["Sample Data", "My Custom Group"],
    )
    # additionalProperties here works around an
    # incompatibility with VSCode's Red Hat YAML validator
    options: Dict[str, Any] = Field(
        {},
        additionalProperties=True,
        title="Task Options",
        description="Options for the task. Tasks in CumulusCI can accept specific options. Use cci task info to list available options for a particular task.",
        examples=[{"path": "src"}],
    )
    ui_options: StepUIOptions = Field(
        {},
        additionalProperties=True,
        title="UI Options",
        description="Options for the task or flow that are only used by MetaDeploy. For flows, this should be a dictionary with a key for the task name containing keys for each option.",
        examples=[
            {"name": "Deploy Recommended Config", "is_recommended": True},
            {"name": "Deploy Optional Config", "is_optional": True},
        ],
    )
    name: Optional[str] = None  # get rid of this???

    class Config:
        title = "Task Definition"
        description = "A task to run in a flow. Tasks are Python classes that perform a specific action."


class Flow(CCIDictModel):
    description: str = Field(
        None,
        title="Description",
        description="A description of the flow shown via the cli in flow list, flow info, and when running the flow.",
        examples=["Sets up a new dev org."],
    )
    steps: Dict[str, Step] = Field(
        None,
        title="Steps",
        description="The steps in the flow. Steps are entered in numbered slots using the key. Slot numbers are parsed with Python's LooseVersion to allow for injecting steps between other steps using the format 1.1.2.",
        examples=[
            {
                "1": {"task": "deploy"},
                "1.1": {"task": "my-custom-task"},
                "2": {"task": "run_tests"},
            }
        ],
    )
    group: str = Field(
        None,
        title="Group",
        description="The group of the flow. Used to group flows in cci flow list.",
        examples=["Org Setup", "My Custom Group"],
    )

    class Config:
        title = "Flow Definition"
        description = (
            "A flow to run. Flows are a series of steps that can be run in order."
        )


class Package(CCIDictModel):
    name: Optional[str] = Field(
        None,
        title="Package Name",
        description="The name of the package in the packaging org or DevHub.",
        examples=["Nonprofit Success Pack", "My Custom Package"],
    )
    name_managed: Optional[str] = Field(
        None,
        title="Managed Package Name Override",
        description="If set, this will override the package name for deployments to the 1GP managed packages. Use if you need to have a different package name in the 1GP packaging org than in all other orgs.",
        examples=["My Custom 1GP Package Name"],
    )
    namespace: Optional[str] = Field(
        None,
        title="Package Namespace",
        description="The Salesforce assigned package namespace for the package.",
        examples=["npsp", "mynamespace"],
    )
    install_class: str = Field(
        None,
        title="Install Class",
        description="The name of the Apex class to run during package install. This value is used when creating managed package versions.",
        examples=["npsp.InstallScript"],
    )
    uninstall_class: str = Field(
        None,
        title="Uninstall Class",
        description="The name of the Apex class to run during package uninstall. This value is used when creating managed package versions.",
        examples=["npsp.UninstallScript"],
    )
    api_version: str = Field(
        None,
        title="API Version",
        description="The API version to use when deploying and retrieving the project.",
        examples=["50.0"],
    )
    metadata_package_id: str = Field(
        None,
        title="Metadata Package ID",
        description="The Metadata Package ID for 2GP packages.",
        examples=["033000000000000AAA"],
    )

    class Config:
        title = "Package Configuration"
        description = "The package configuration for the project."


class Test(CCIDictModel):
    name_match: str = Field(
        ...,
        title="Apex Test Name Match",
        description="A SOQL LIKE expression to match Apex test class names to run.",
        examples=["%Test", "%_test%"],
    )

    class Config:
        title = "Apex Test Configuration"
        description = "The apex test configuration for the project."


class ReleaseNotesParser(CCIDictModel):
    class_path: PythonClassPath = Field(
        ...,
        title="Class Path",
        description="The Python path to the release notes parser class.",
        examples=["cumulusci.core.release_notes.parsers.BaseParser"],
    )
    title: str = Field(
        ...,
        title="Title",
        description="The title of the release notes parser.",
        examples=["Base Release Notes Parser"],
    )

    class Config:
        title = "Release Notes Parsers Configuration"
        description = (
            "A release notes parser to use for generating automated release notes."
        )


class ReleaseNotes(CCIDictModel):
    parsers: Dict[int, ReleaseNotesParser] = Field(
        {},
        title="Parsers",
        description="A dictionary of release notes parsers in execution order.",
        examples=[
            {
                "1": {
                    "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                    "title": "Critical Changes",
                },
                "2": {
                    "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                    "title": "Changes",
                },
                "3": {
                    "class_path": "cumulusci.tasks.release_notes.parser.GithubIssuesParser",
                    "title": "Issues Closed",
                },
                "4": {
                    "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                    "title": "New Metadata",
                },
                "5": {
                    "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                    "title": "Deleted Metadata",
                },
                "6": {
                    "class_path": "cumulusci.tasks.release_notes.parser.InstallLinkParser",
                    "title": "Installation Info",
                },
            }
        ],
    )

    class Config:
        title = "Release Notes Configuration"
        description = "The release notes configuration for the project."


class Git(CCIDictModel):
    repo_url: str = Field(
        None,
        title="Repo URL",
        description="The URL of the repo.",
        examples=["https://github.com/SalesforceFoundation/NPSP"],
    )
    default_branch: str = Field(
        None,
        title="Default Branch",
        description="The default branch of the repo.",
        examples=["main"],
    )
    prefix_feature: str = Field(
        None,
        title="Feature Branch Prefix",
        description="The prefix for feature branches.",
        examples=["feature/"],
    )
    prefix_beta: str = Field(
        None,
        title="Beta Branch Prefix",
        description="The prefix for beta branches.",
        examples=["beta/"],
    )
    prefix_release: str = Field(
        None,
        title="Release Branch Prefix",
        description="The prefix for release branches.",
        examples=["release/"],
    )
    push_prefix_sandbox: str = Field(
        None,
        title="Sandbox Push Prefix",
        description="The prefix for sandbox push branches.",
        examples=["sandbox/"],
    )
    push_prefix_production: str = Field(
        None,
        title="Production Push Prefix",
        description="The prefix for production push branches.",
        examples=["prod/"],
    )
    release_notes: ReleaseNotes = Field(
        None,
        title="Release Notes",
        description="The release notes configuration.",
        examples=[
            {
                "parsers": {
                    "1": {
                        "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                        "title": "Critical Changes",
                    },
                    "2": {
                        "class_path": "cumulusci.tasks.release_notes.parser.GithubLinesParser",
                        "title": "Changes",
                    },
                }
            }
        ],
    )
    two_gp_context: str = Field(
        None,
        alias="2gp_context",
        title="2GP Context",
        description="The GitHub Commit Status name to use for 2GP feature packages.",
        examples=["Build Feature Test Package", "Nonstandard Package Status"],
    )
    unlocked_context: Optional[str] = Field(
        None,
        title="Unlocked Context",
        description="The GitHub Commit Status name to use for unlocked packages.",
        examples=["Build Unlocked Package", "Nonstandard Package Status"],
    )

    class Config:
        title = "Git Configuration"
        description = "The git configuration for the project."


class Plan(CCIDictModel):  # MetaDeploy plans
    title: str = Field(
        None,
        title="Plan Title",
        description="The title of the plan, shown in MetaDeploy.",
        examples=["Base Install", "Full Demo Install"],
    )
    description: str = Field(
        None,
        title="Description",
        description="A description of the plan.",
        examples=[
            "A base install of the packages only",
            "A full demo install of the packages with configuration and sample data",
        ],
    )
    tier: Literal["primary", "secondary", "additional"] = Field(
        "primary",
        title="Tier",
        description="The tier of the plan. Primary plans are shown first in MetaDeploy. Secondary plans are shown second. Additional plans are shown last. Only one primary plan and one secondary plan can be set per project. You can set multiple additional plans.",
        examples=["primary", "secondary", "additional"],
    )
    slug: str = Field(
        None,
        title="Slug",
        description="The slug of the plan, used in the plan URL.",
        examples=["base-install", "full-demo-install"],
    )
    is_listed: bool = Field(
        True,
        title="Is Listed",
        description="If True, the plan is listed in MetaDeploy. If False, the plan is hidden.",
    )
    steps: Dict[str, Step] = Field(
        None,
        title="Steps",
        description="The steps in the plan. Steps are entered in numbered slots using the key. Slot numbers are parsed with Python's LooseVersion to allow for injecting steps between other steps using the format 1.1.2.",
        examples=[
            {
                "1": {"task": "update_dependencies"},
                "2": {"task": "install_prod"},
            },
            {
                "1": {"task": "update_dependencies"},
                "2": {"task": "install_prod"},
                "3": {"flow": "config_common"},
                "4": {"flow": "config_demo"},
                "5": {"flow": "demo_data"},
            },
            {
                "1": {"flow": "customer_org"},
            },
            {
                "1": {"task": "customer_org_full"},
            },
        ],
    )
    checks: List[PreflightCheck] = Field(
        [],
        title="Preflight Checks",
        description="A list of preflight checks to run before the plan.",
        examples=[
            [
                {
                    "when": "org.scratch == True",
                    "action": "error",
                    "message": "The org must be a scratch org.",
                },
                {
                    "when": "'npsp' not in tasks.get_installed_packages()",
                    "action": "error",
                    "message": "NPSP must be installed in your org.",
                },
            ]
        ],
    )
    error_message: str = Field(
        None,
        title="Error Message",
        description="The error message to display if the preflight check is triggered.",
        examples=["The org must be a scratch org."],
    )
    post_install_message: str = Field(
        None,
        title="Post-install Message",
        description="The message to display after the plan is installed.",
        examples=["The plan has been installed."],
    )
    preflight_message: str = Field(
        None,
        title="Preflight Message",
        description="The message to display before the plan is installed.",
        examples=[
            "The plan is about to be installed. We're running some checks on your org first."
        ],
    )
    allowed_org_providers: List[Literal["devhub", "user"]] = Field(
        ["user"],
        title="Allowed Org Providers",
        description="The org providers that are allowed for the plan. The user provider allows connections to existing orgs using OAuth. The devhub provider uses MetaDeploy's configured DevHub to create scratch orgs.",
        examples=[["devhub"], ["user"], ["devhub", "user"]],
    )

    class Config:
        title = "Plan Definition"
        description = "A plan to install in MetaDeploy. See https://metadeploy.readthedocs.io for more information."


class ResolutionStrategiesEnum(StrEnum):
    """The allowed values for the resolution_strategy field of a dependency resolution"""

    latest_release = "latest_release"
    include_beta = "include_beta"
    commit_status = "commit_status"
    unlocked = "unlocked"


class DependencyResolutions(CCIDictModel):
    production: Union[ResolutionStrategiesEnum, str] = Field(
        None,
        title="Production Resolution",
        description="The resolution strategy to use for production orgs including packaging orgs and promotable package versions.",
        examples=["latest_release"],
    )
    preproduction: str = Field(
        None,
        title="Preproduction Resolution",
        description="The resolution strategy to use for preproduction orgs including scratch orgs.",
        examples=["include_beta", "commit_status", "my_custom_strategy"],
    )
    resolution_strategies: Dict[str, List[str]] = Field(
        None,
        title="Resolution Strategies",
        description="A dictionary of resolution strategies made up of a list of resolvers run in order until resolution is found.",
        examples=[
            {
                "latest_release": ["tag", "latest_release", "unmanaged"],
                "include_beta": ["tag", "latest_beta", "latest_release", "unmanaged"],
            }
        ],
    )

    class Config:
        title = "Dependency Resolutions"
        description = "The dependency resolution configuration for the project. See https://cumulusci.readthedocs.io/en/stable/dev.html#manage-dependencies for more information."


class Project(CCIDictModel):
    name: Optional[str] = Field(
        None,
        title="Project Name",
        description="The name of the project. This should generally match the git repo name. This name is used as the project name in CumulusCI's keychain for storing files under ~/.cumulusci.",
        examples=["NPSP", "My-Repo"],
    )
    package: Optional[Package] = Field(
        None,
        title="Package Config",
        description="The package info for the project.",
        examples=[
            {
                "name": "Nonprofit Success Pack",
                "namespace": "npsp",
                "api_version": "59.0",
            }
        ],
    )
    test: Optional[Test] = Field(
        None,
        title="Apex Testing Config",
        description="The apex test configuration for the project.",
        examples=[{"name_match": "%Test"}, {"name_match": "%_test%"}],
    )
    git: Optional[Git] = Field(
        None,
        title="Git Config",
        description="The git configuration for the project.",
        examples=[
            {
                "repo_url": "https://github.com/SalesforceFoundation/NPSP",
                "default_branch": "main",
                "prefix_feature": "feature/",
                "prefix_beta": "beta/",
                "prefix_release": "release/",
                "push_prefix_sandbox": "sandbox/",
                "push_prefix_production": "prod/",
            }
        ],
    )
    dependencies: Optional[List[Dict[str, str]]] = Field(
        None,
        title="Dependencies",
        description="A list of dependencies for the project. See https://cumulusci.readthedocs.io/en/stable/dev.html#manage-dependencies for more information.",
        examples=[
            [
                {"namespace": "somens", "version": "1.23"},
                {"github": "https://github.com/SalesforceFoundation/NPSP"},
            ],
        ],
    )
    dependency_resolutions: Optional[DependencyResolutions] = Field(
        None,
        title="Dependency Resolutions",
        description="The dependency resolution configuration for the project. See https://cumulusci.readthedocs.io/en/stable/dev.html#manage-dependencies for more information.",
        examples=[
            {
                "production": "latest_release",
                "preproduction": "include_beta",
                "resolution_strategies": {
                    "latest_release": ["tag", "latest_release", "unmanaged"],
                    "include_beta": [
                        "tag",
                        "latest_beta",
                        "latest_release",
                        "unmanaged",
                    ],
                },
            }
        ],
    )
    dependency_pins: Optional[List[Dict[str, str]]] = Field(
        None,
        title="Dependency Pins",
        description="A list of dependency pins for the project. See https://cumulusci.readthedocs.io/en/stable/dev.html#manage-dependencies for more information.",
        examples=[
            [
                {
                    "github": "https://github.com/SalesforceFoundation/NPSP",
                    "tag": "rel/3.219",
                },
                {
                    "github": "https://github.com/SalesforceFoundation/Contacts_and_Organizations",
                    "tag": "rel/3.19",
                },
            ],
        ],
    )
    source_format: Literal["sfdx", "mdapi"] = Field(
        "mdapi",
        title="Source Format",
        description="The source format for the project. Either sfdx for sfdx source format under force-app/ or mdapi for Metadata API format under src/.",
        examples=["sfdx", "mdapi"],
    )
    custom: Optional[Dict] = Field(
        None,
        title="Custom",
        description="A dictionary for custom project configuration. This is a good place to put project-specific configuration. Do not use for storing any sensitive information like credentials!",
        examples=[{"my_custom_key": "my_custom_value"}],
    )

    class Config:
        title = "Project Configuration"
        description = "The project configuration for the project. See https://cumulusci.readthedocs.io/en/stable/config.html for more information."


class ScratchOrg(CCIDictModel):
    config_file: Path = Field(
        None,
        title="Config File",
        description="The path to the scratchdef config file.",
        examples=[
            "orgs/dev.json",
            "orgs/managed.json",
            "config/project-scratch-def.json",
        ],
    )
    days: int = Field(
        None,
        title="Days",
        description="The number of days the scratch org should last.",
        min=1,
        max=30,
        examples=[1, 7, 30],
    )
    namespaced: bool = Field(
        None,
        title="Namespaced",
        description="If true, the scratch org should be created with the project's namespace. If false, the scratch org should be created without a namespace.",
        examples=[True, False],
    )
    setup_flow: str = Field(
        None,
        title="Setup Flow",
        description="The name of the flow to run after the scratch org is created.",
        examples=["dev_org", "qa_org_2gp"],
    )
    noancestors: bool = Field(
        None,
        title="No Ancestors",
        description="If True, the scratch org should be created without ancestors.",
        examples=[True, False],
    )
    release: Literal["preview", "previous"] = Field(
        None,
        title="Release",
        description="The Salesforce release to use for the scratch org.",
        examples=["preview", "previous"],
    )

    class Config:
        title = "Scratch Org Configuration"
        description = "The scratch org configuration for the project. See https://cumulusci.readthedocs.io/en/stable/config.html#scratch-org-configurations for more information."


class Orgs(CCIDictModel):
    scratch: Dict[str, ScratchOrg] = Field(
        None,
        title="Scratch Org Configs",
        description="A dictionary of scratch org configurations for the project.",
        examples=[
            {
                "dev": {
                    "config_file": "orgs/dev.json",
                    "days": 1,
                    "namespaced": True,
                    "setup_flow": "dev_org",
                    "noancestors": True,
                    "release": "preview",
                },
                "qa": {
                    "config_file": "orgs/qa.json",
                    "days": 7,
                    "namespaced": True,
                    "setup_flow": "qa_org",
                    "noancestors": True,
                    "release": "previous",
                },
            }
        ],
    )

    class Config:
        title = "Orgs Configuration"
        description = "The orgs configuration for the project."


class ServiceAttribute(CCIDictModel):
    description: str = Field(
        None,
        title="Description",
        description="A description of the attribute.",
        examples=["The username for the service."],
    )
    required: bool = Field(
        None,
        title="Required",
        description="If True, the attribute is required.",
        examples=[True, False],
    )
    default_factory: PythonClassPath = Field(
        None,
        title="Default Factory",
        description="The Python class path to a callable that returns the default value for the attribute.",
        examples=["cumulusci.core.config.OrgConfig.default_username"],
    )
    default: str = Field(
        None,
        title="Default",
        description="The default value for the attribute.",
        examples=["my_default_username"],
    )
    sensitive: bool = Field(
        False,
        title="Sensitive",
        description="If True, the attribute is sensitive and should not be logged.",
        examples=[True, False],
    )

    class Config:
        title = "Service Attribute Definition"
        description = "An attribute for a service."


class Service(CCIDictModel):
    description: str = Field(
        None,
        title="Description",
        description="A description of the service.",
        examples=["Create a connection to GitHub to interact with the API."],
    )
    class_path: Optional[str] = Field(
        None,
        title="Class Path",
        description="The Python class path to the service class. Typically not used for most services that just need simple key/value configuration.",
        examples=[
            "cumulusci.core.config.marketing_cloud_service_config.MarketingCloudServiceConfig"
        ],
    )
    attributes: Dict[str, ServiceAttribute] = Field(
        None,
        title="Attributes",
        description="A dictionary of attributes for the service.",
        examples=[
            {
                "username": {
                    "description": "The username for the service.",
                    "required": True,
                    "default_factory": "cumulusci.core.config.OrgConfig.default_username",
                },
                "password": {
                    "description": "The password for the service.",
                    "required": True,
                    "sensitive": True,
                },
            },
            {
                "base_url": {
                    "description": "The base URL for the service.",
                    "required": True,
                    "default": "https://my-service.com",
                },
                "api_token": {
                    "description": "The API token for the service.",
                    "required": True,
                    "sensitive": True,
                },
            },
        ],
    )
    validator: PythonClassPath = Field(
        None,
        title="Validator",
        description="The Python class path to a callable that validates the service configuration.",
        examples=["cumulusci.core.github.validate_service"],
    )

    class Config:
        title = "Service Definition"
        description = "A service for the project."


class CumulusCIConfig(CCIDictModel):
    keychain: PythonClassPath = Field(
        ...,
        title="Keychain Class Path",
        description="The Python class path to the keychain class to override CumulusCI's keychain.",
        examples=[
            "cumulusci.core.keychain.EnvironmentProjectKeychain",
            "mypypackage.keychain.MyCumulusCIKeychain",
        ],
    )

    class Config:
        title = "CumulusCI Configuration"
        description = "The CumulusCI configuration for the project."


class GitHubSourceRelease(StrEnum):
    LATEST = "latest"
    PREVIOUS = "previous"
    LATEST_BETA = "latest_beta"


class GitHubSourceModel(HashableBaseModel):
    github: str = Field(
        ...,
        title="GitHub URL",
        description="The GitHub URL for the repository.",
        examples=["https://github.com/SalesforceFoundation/NPSP"],
    )
    resolution_strategy: Optional[str] = Field(
        None,
        title="Resolution Strategy",
        description="The resolution strategy to use for the GitHub source.",
        examples=["latest_release", "include_beta", "commit_status", "unlocked"],
    )
    commit: Optional[str] = Field(
        None,
        title="Commit",
        description="The commit to use for the GitHub source.",
        examples=["abc123"],
    )
    ref: Optional[str] = Field(
        None,
        title="Ref",
        description="The ref to use for the GitHub source.",
        examples=["main"],
    )
    branch: Optional[str] = Field(
        None,
        title="Branch",
        description="The branch to use for the GitHub source.",
        examples=["main"],
    )
    tag: Optional[str] = Field(
        None,
        title="Tag",
        description="The tag to use for the GitHub source.",
        examples=["v1.0"],
    )
    release: Optional[GitHubSourceRelease] = Field(
        None,
        title="Release",
        description="The release to use for the GitHub source.",
        examples=["latest", "previous", "latest_beta"],
    )
    description: Optional[str] = Field(
        None,
        title="Description",
        description="A description of the source.",
        examples=["The GitHub source for the Nonprofit Success Pack."],
    )
    allow_remote_code: Optional[bool] = Field(
        False,
        title="Allow Remote Code",
        description="If True, allow remote code execution for the source. This is a security risk and should only be used for trusted sources.",
        examples=[True, False],
    )

    class Config:
        title = "GitHub Source Definition"
        description = "A GitHub source for the project. See https://cumulusci.readthedocs.io/en/stable/config.html#tasks-and-flows-from-a-different-project for more information."

    @root_validator
    def validate(cls, values):
        exclusive_keys = [
            "resolution_strategy",
            "commit",
            "ref",
            "branch",
            "tag",
            "release",
        ]
        key_count = len([x for x in exclusive_keys if x in values and values[x]])
        if key_count > 1:
            raise ValueError(
                'Sources must use only one of "resolution_strategy", "commit", "ref", "branch", "tag", or "release".'
            )
        elif key_count == 0:
            values["resolution_strategy"] = "production"

        return values


class LocalFolderSourceModel(HashableBaseModel):
    path: DirectoryPath = Field(
        ...,
        title="Folder Path",
        description="The path to the folder.",
        examples=["modules"],
    )
    allow_remote_code: Optional[bool] = Field(
        False,
        title="Allow Remote Code",
        description="If True, allow remote code execution for the source. This is a security risk and should only be used for trusted sources.",
        examples=[True, False],
    )

    class Config:
        title = "Local Folder Source Definition"
        description = "A local folder source for the project. See https://cumulusci.readthedocs.io/en/stable/config.html#tasks-and-flows-from-a-different-project for more information."


class CumulusCLIConfig(CCIDictModel):
    show_stacktraces: bool = Field(
        False,
        title="Show Stacktraces",
        description="If True, show stacktraces for exceptions.",
        examples=[True, False],
    )
    plain_output: bool = Field(
        None,
        title="Plain Output",
        description="If True, use plain output instead of rich output.",
        examples=[True, False],
    )

    class Config:
        title = "CumulusCI CLI Configuration"
        description = "The CumulusCI CLI configuration for the project."


class CumulusCIRoot(CCIDictModel):
    tasks: Dict[str, Task] = Field(
        {},
        title="Tasks",
        description="A dictionary of tasks for the project.",
        examples=[
            {
                "deploy": {
                    "class_path": "cumulusci.tasks.salesforce.Deploy",
                    "description": "Deploys the metadata in the project to the org.",
                    "group": "Deployment",
                    "options": {"path": "src"},
                },
                "load_custom_settings": {
                    "class_path": "cumulusci.tasks.salesforce.LoadCustomSettings",
                    "description": "Loads custom settings data into the org.",
                    "group": "Data",
                    "options": {"path": "data/custom_settings"},
                },
            }
        ],
    )
    flows: Dict[str, Flow] = Field(
        {},
        title="Flows",
        description="A dictionary of flows for the project.",
        examples=[
            {
                "dependencies": {
                    "description": "Installs all dependencies for the project.",
                    "steps": {
                        "1": {"task": "update_dependencies"},
                        "2": {"task": "install_prod"},
                    },
                },
                "config_dev": {
                    "description": "Configures the org for development.",
                    "steps": {
                        "1": {"flow": "config_common"},
                        "2": {"flow": "config_dev"},
                    },
                },
                "dev_org": {
                    "description": "Sets up a new dev org.",
                    "steps": {
                        "1": {"flow": "dependencies"},
                        "2": {"flow": "deploy_unmanaged"},
                        "3": {"flow": "config_dev"},
                    },
                },
            }
        ],
    )
    project: Project = Field(
        {},
        title="Project",
        description="The project configuration.",
        examples=[
            {
                "name": "Nonprofit Success Pack",
                "package": {
                    "name": "Nonprofit Success Pack",
                    "namespace": "npsp",
                    "api_version": "59.0",
                },
                "test": {"name_match": "%Test"},
                "git": {
                    "repo_url": "https://github.com/SalesforceFoundation/NPSP",
                    "default_branch": "main",
                    "prefix_feature": "feature/",
                    "prefix_beta": "beta/",
                    "prefix_release": "release/",
                    "push_prefix_sandbox": "sandbox/",
                    "push_prefix_production": "prod/",
                },
                "dependencies": [
                    {"namespace": "somens", "version": "1.23"},
                    {"github": "https://github.com/SalesforceFoundation/Households"},
                ],
                "dependency_resolutions": {
                    "production": "latest_release",
                    "preproduction": "include_beta",
                    "resolution_strategies": {
                        "latest_release": ["tag", "latest_release", "unmanaged"],
                        "include_beta": [
                            "tag",
                            "latest_beta",
                            "latest_release",
                            "unmanaged",
                        ],
                    },
                },
            }
        ],
    )
    orgs: Orgs = Field(
        {},
        title="Orgs",
        description="A dictionary of org configurations for the project.",
        examples=[
            {
                "scratch": {
                    "dev": {
                        "config_file": "orgs/dev.json",
                        "days": 1,
                        "namespaced": True,
                        "setup_flow": "dev_org",
                        "noancestors": True,
                        "release": "preview",
                    },
                    "qa": {
                        "config_file": "orgs/qa.json",
                        "days": 7,
                        "namespaced": True,
                        "setup_flow": "qa_org",
                        "noancestors": True,
                        "release": "previous",
                    },
                }
            }
        ],
    )
    services: Dict[str, Service] = Field(
        {},
        title="Services",
        description="A dictionary of services for the project.",
        examples=[
            {
                "github": {
                    "description": "Create a connection to GitHub to interact with the API.",
                    "attributes": {
                        "username": {
                            "description": "The username for the service.",
                            "required": True,
                            "default_factory": "cumulusci.core.config.OrgConfig.default_username",
                        },
                        "password": {
                            "description": "The password for the service.",
                            "required": True,
                            "sensitive": True,
                        },
                    },
                    "validator": "cumulusci.core.github.validate_service",
                }
            }
        ],
    )
    cumulusci: CumulusCIConfig = Field(
        None,
        title="CumulusCI",
        description="The CumulusCI configuration.",
        examples=[
            {
                "keychain": "cumulusci.core.keychain.EnvironmentProjectKeychain",
            }
        ],
    )
    plans: Dict[str, Plan] = Field(
        {},
        title="Plans",
        description="A dictionary of plans for the project.",
        examples=[
            {
                "base_install": {
                    "title": "Base Install",
                    "description": "A base install of the packages only",
                    "tier": "primary",
                    "slug": "base-install",
                    "is_listed": True,
                    "steps": {
                        "1": {"task": "update_dependencies"},
                        "2": {"task": "install_prod"},
                    },
                    "checks": [
                        {
                            "when": "org.scratch == True",
                            "action": "error",
                            "message": "The org must be a scratch org.",
                        },
                        {
                            "when": "'npsp' not in tasks.get_installed_packages()",
                            "action": "error",
                            "message": "NPSP must be installed in your org.",
                        },
                    ],
                    "error_message": "The org must be a scratch org.",
                    "post_install_message": "The plan has been installed.",
                    "preflight_message": "The plan is about to be installed. We're running some checks on your org first.",
                    "allowed_org_providers": ["devhub", "user"],
                },
                "full_demo_install": {
                    "title": "Full Demo Install",
                    "description": "A full demo install of the packages with configuration and sample data",
                    "tier": "secondary",
                    "slug": "full-demo-install",
                    "is_listed": True,
                    "steps": {
                        "1": {"task": "update_dependencies"},
                        "2": {"task": "install_prod"},
                        "3": {"flow": "config_common"},
                        "4": {"flow": "config_demo"},
                        "5": {"flow": "demo_data"},
                    },
                    "checks": [
                        {
                            "when": "org.scratch == True",
                            "action": "error",
                            "message": "The org must be a scratch org.",
                        },
                        {
                            "when": "'npsp' not in tasks.get_installed_packages()",
                            "action": "error",
                            "message": "NPSP must be installed in your org.",
                        },
                    ],
                    "error_message": "The org must be a scratch org.",
                    "post_install_message": "The plan has been installed.",
                    "preflight_message": "The plan is about to be installed. We're running some checks on your org first.",
                    "allowed_org_providers": ["devhub", "user"],
                },
                "customer_org": {
                    "title": "Customer Org",
                    "description": "A customer org with the packages installed",
                    "tier": "additional",
                    "slug": "customer-org",
                    "is_listed": True,
                    "steps": {
                        "1": {"flow": "customer_org"},
                    },
                    "checks": [
                        {
                            "when": "org.scratch == True",
                            "action": "error",
                            "message": "The org must be a scratch org.",
                        },
                        {
                            "when": "'npsp' not in tasks.get_installed_packages()",
                            "action": "error",
                            "message": "NPSP must be installed in your org.",
                        },
                    ],
                    "error_message": "The org must be a scratch org.",
                    "post_install_message": "The plan has been installed.",
                    "preflight_message": "The plan is about to be installed. We're running some checks on your org first.",
                    "allowed_org_providers": ["devhub", "user"],
                },
                "customer_org_full": {
                    "title": "Customer Org Full",
                    "description": "A customer org with the packages installed and configured",
                    "tier": "additional",
                    "slug": "customer-org-full",
                    "is_listed": True,
                    "steps": {
                        "1": {"task": "customer_org_full"},
                    },
                    "checks": [
                        {
                            "when": "org.scratch == True",
                            "action": "error",
                            "message": "The org must be a scratch org.",
                        },
                        {
                            "when": "'npsp' not in tasks.get_installed_packages()",
                            "action": "error",
                            "message": "NPSP must be installed in your org.",
                        },
                    ],
                    "error_message": "The org must be a scratch org.",
                    "post_install_message": "The plan has been installed.",
                    "preflight_message": "The plan is about to be installed. We're running some checks on your org first.",
                    "allowed_org_providers": ["devhub", "user"],
                },
            }
        ],
    )
    minimum_cumulusci_version: str = Field(
        None,
        title="Minimum CumulusCI Version",
        description="The minimum version of CumulusCI required to run the project.",
        examples=["3.0.0"],
    )
    sources: Dict[str, Union[LocalFolderSourceModel, GitHubSourceModel]] = Field(
        {},
        title="Sources",
        description="A dictionary of sources for the project.",
        examples=[
            {
                "npsp": {
                    "github": "https://github.com/SalesforceFoundation/NPSP",
                    "resolution_strategy": "latest_release",
                },
                "pmm": {
                    "github": "https://github.com/SalesforceFoundation/PMM",
                    "resolution_strategy": "latest_release",
                },
            },
        ],
    )
    cli: CumulusCLIConfig = Field(
        None,
        title="CumulusCI CLI",
        description="The CumulusCI CLI configuration.",
        examples=[
            {
                "show_stacktraces": False,
                "plain_output": False,
            }
        ],
    )

    class Config:
        title = "CumulusCI Project Configuration"
        description = "The root configuration for the project."

    @validator("plans")
    def validate_plan_tiers(cls, plans):
        existing_tiers = [plan.tier for plan in plans.values()]
        has_duplicate_tiers = any(
            existing_tiers.count(tier) > 1 for tier in ("primary", "secondary")
        )
        if has_duplicate_tiers:
            raise ValueError("Only one plan can be defined as 'primary' or 'secondary'")
        return plans


class CumulusCIFile(CCIDictModel):
    __root__: Union[CumulusCIRoot, None]


def parse_from_yaml(source) -> dict:
    "Parse from a path, url, path-like or file-like"
    return CumulusCIFile.parse_from_yaml(source) or {}


def validate_data(
    data: Union[dict, list],
    context: str = None,
    on_error: callable = None,
):
    """Validate data which has already been loaded into a dictionary or list.

    context is a string that will be used to give context to error messages.
    on_error will be called for any validation errors with a dictionary in Pydantic error format

    https://pydantic-docs.helpmanual.io/usage/models/#error-handling
    """
    return CumulusCIFile.validate_data(data, context=context, on_error=on_error)


class ErrorDict(TypedDict):
    "The structure of a Pydantic error dictionary. Google TypedDict if its new to you."
    loc: Sequence[Union[str, int]]
    msg: str
    type: str


has_shown_yaml_error_message = False


def _log_yaml_errors(logger, errors: List[ErrorDict]):
    "Format and log a Pydantic-style error dictionary"
    global has_shown_yaml_error_message
    plural = "" if len(errors) <= 1 else "s"
    logger.warning(f"CumulusCI Configuration Warning{plural}:")
    for error in errors:
        loc = " -> ".join(repr(x) for x in error["loc"] if x != "__root__")
        logger.warning("  %s\n    %s", loc, error["msg"])
    if not has_shown_yaml_error_message:
        logger.error(
            "NOTE: These warnings will become errors on Sept 30, 2022.\n\n"
            "If you need to put non-standard data in your CumulusCI file "
            "(for some form of project-specific setting), put it in "
            "the `project: custom:` section of `cumulusci.yml` ."
        )
        logger.error(
            "If you think your YAML has no error, please report the bug to the CumulusCI team."
        )
        logger.error("https://github.com/SFDO-Tooling/CumulusCI/issues/\n")
        has_shown_yaml_error_message = True


def cci_safe_load(
    source: DataInput, context: str = None, on_error: callable = None, logger=None
) -> dict:
    """Load a CumulusCI.yml file and issue warnings for unknown structures."""
    errors = []
    assert not (
        on_error and logger
    ), "Please specify either on_error or logger but not both"
    on_error = on_error or errors.append

    logger = logger or default_logger

    with load_from_source(source) as (data_stream, filename):
        data = load_yaml_data(data_stream, filename)
        context = context or filename

        try:
            validate_data(data, context=context, on_error=on_error)
            if errors:
                _log_yaml_errors(logger, errors)
        except Exception as e:
            # should never be executed
            print(f"Error validating cumulusci.yml {e}")
            if on_error:
                on_error(
                    {
                        "loc": (context,),
                        "msg": f"Error validating cumulusci.yml {e}",
                        "type": "exception",
                    }
                )
            pass
        return data or {}


def _validate_files(globs):
    "Validate YML files from Dev CLI for smoke testing"

    from glob import glob

    errors = []
    for g in globs:
        print(g)
        filenames = glob(g, recursive=True)
        for filename in filenames:
            print("Validating", filename)

            cci_safe_load(filename, filename, on_error=errors.append)
    return errors


def _validate_url(url):  # pragma: no cover
    "Validate YML URL from Dev CLI for smoke testing"
    errors = []
    cci_safe_load(url, url, on_error=errors.append)
    return errors


# validate YML files as a CLI for smoke testing
if __name__ == "__main__":  # pragma: no cover
    import sys
    from pprint import pprint

    if sys.argv[1].startswith("http"):
        pprint(_validate_url(sys.argv[1]))
    else:
        pprint(_validate_files(sys.argv[1:]))
