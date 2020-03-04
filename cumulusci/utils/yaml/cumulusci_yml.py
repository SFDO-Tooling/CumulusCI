from typing import Dict, List, Any, Optional, Union
from typing_extensions import Literal
from yaml import safe_load
from pathlib import Path

from cumulusci.utils.yaml.model_parser import CCIDictModel, ErrorHandling


PythonClass = str
URL = str


class FlowOrTask(CCIDictModel):
    def __init__(self, **kwargs):
        assert "flow" in kwargs or "task" in kwargs

    flow: str = None
    task: str = None
    options: Dict[str, Any] = {}
    ignore_failure: bool = None


class TaskUIOptions(CCIDictModel):
    name: str = None


class TaskReference(CCIDictModel):
    task: str
    options: Dict[str, Any] = {}
    ui_options: Dict[str, Dict[int, TaskUIOptions]] = {}


class Task(CCIDictModel):
    name: str = None  # is this real or a typo
    class_path: str = None
    description: str = None
    options: Dict[str, Any] = None
    group: str = None
    ui_options: TaskUIOptions = None


class Flow(CCIDictModel):
    description: str = None
    steps: Dict[str, FlowOrTask]
    group: str = None


class Package(CCIDictModel):
    name: Optional[str] = None
    name_managed: Optional[str] = None
    namespace: Optional[str] = None
    install_class: str = None
    uninstall_class: str = None
    api_version: str = None


class Test(CCIDictModel):
    name_match: str


class Parser(CCIDictModel):
    class_path: PythonClass
    title: str


class ReleaseNotes(CCIDictModel):
    parsers: Dict[int, Parser]  # should probably be a list


class Git(CCIDictModel):
    repo_url: str = None
    default_branch: str = None
    prefix_feature: str = None
    prefix_beta: str = None
    prefix_release: str = None
    push_prefix_sandbox: str = None
    push_prefix_production: str = None
    release_notes: ReleaseNotes = None


class ApexDoc(CCIDictModel):
    homepage: str
    banner: str
    branch: str
    repo_dir: Path


class Check(CCIDictModel):
    when: str = None
    action: str = None
    message: str = None


class Plan(CCIDictModel):  # MetaDeploy plans
    title: str
    description: str = None
    tier: str = None
    slug: str = None
    is_listed: bool = None
    steps: Dict[str, FlowOrTask] = None
    checks: List[Check] = None
    group: str = None


class Project(CCIDictModel):
    name: Optional[str]
    package: Package = None
    test: Test = None
    git: Git = None
    dependencies: List[Dict[str, URL]] = None  # TODO
    apexdoc: ApexDoc = None
    source_format: Literal["sfdx", "mdapi"] = "mdapi"


class ScratchOrg(CCIDictModel):
    config_file: Path
    days: int = None
    namespaced: str = None


class Orgs(CCIDictModel):
    scratch: Dict[str, ScratchOrg]


class Attribute(CCIDictModel):
    description: str
    required: bool


class Service(CCIDictModel):
    description: str
    attributes: Dict[str, Attribute]
    validator: PythonClass = None


class CumulusCI(CCIDictModel):
    keychain: PythonClass


class CumulusCI(CCIDictModel):
    tasks: Dict[str, Task] = {}
    flows: Dict[str, Flow] = {}
    project: Project = {}
    orgs: Orgs = {}
    services: Dict[str, Service] = {}
    cumulusci: CumulusCI = None
    plans: Dict[str, Plan] = None
    minimum_cumulusci_version: str = None


class Document(CCIDictModel):
    __root__: CumulusCI


def parse_mapping_from_yaml(source):
    return Document.parse_from_yaml(source)


def validate_data(
    data: Union[dict, list],
    context: str = None,
    on_error: ErrorHandling = "raise",
    logfunc: callable = None,
):
    return Document.validate_data(
        data, context=context, on_error=on_error, logfunc=logfunc
    )


def cci_safe_load(
    source,
    context: str = None,
    on_error: ErrorHandling = "warn",
    logfunc: callable = None,
):
    """Transitional function for testing validator before depending upon it."""
    data = safe_load(source)
    try:
        validate_data(data, context=context, on_error=on_error, logfunc=logfunc)
    except Exception as e:
        # should never be executed
        print(f"Error validating cumulusci.yml {e}")
        if logfunc:
            logfunc(f"Error validating cumulusci.yml {e}")
        pass
    return data
