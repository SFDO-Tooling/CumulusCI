from typing import Dict, List, Any, Optional
from typing_extensions import Literal

from pathlib import Path

from cumulusci.utils.yaml.model_parser import CCIBaseModel


PythonClass = str
URL = str


class FlowOrTask(CCIBaseModel):
    def __init__(self, **kwargs):
        assert "flow" in kwargs or "task" in kwargs

    flow: str = None
    task: str = None
    options: Dict[str, Any] = {}
    ignore_failure: bool = None


class TaskUIOptions(CCIBaseModel):
    name: str = None


class TaskReference(CCIBaseModel):
    task: str
    options: Dict[str, Any] = {}
    ui_options: Dict[str, Dict[int, TaskUIOptions]] = {}


class Task(CCIBaseModel):
    name: str = None  # is this real or a typo
    class_path: str = None
    description: str = None
    options: Dict[str, Any] = None
    group: str = None
    ui_options: TaskUIOptions = None


class Flow(CCIBaseModel):
    description: str = None
    steps: Dict[str, FlowOrTask]
    group: str = None


class Package(CCIBaseModel):
    name: Optional[str] = None
    name_managed: Optional[str] = None
    namespace: Optional[str] = None
    install_class: str = None
    uninstall_class: str = None
    api_version: str = None


class Test(CCIBaseModel):
    name_match: str


class Parser(CCIBaseModel):
    class_path: PythonClass
    title: str


class ReleaseNotes(CCIBaseModel):
    parsers: Dict[int, Parser]  # should probably be a list


class Git(CCIBaseModel):
    repo_url: str = None
    default_branch: str = None
    prefix_feature: str = None
    prefix_beta: str = None
    prefix_release: str = None
    push_prefix_sandbox: str = None
    push_prefix_production: str = None
    release_notes: ReleaseNotes = None


class ApexDoc(CCIBaseModel):
    homepage: str
    banner: str
    branch: str
    repo_dir: Path


class Check(CCIBaseModel):
    when: str = None
    action: str = None
    message: str = None


class Plan(CCIBaseModel):  # MetaDeploy plans
    title: str
    description: str = None
    tier: str = None
    slug: str = None
    is_listed: bool = None
    steps: Dict[str, FlowOrTask] = None
    checks: List[Check] = None
    group: str = None


class Project(CCIBaseModel):
    name: Optional[str]
    package: Package = None
    test: Test = None
    git: Git = None
    dependencies: List[Dict[str, URL]] = None  # TODO
    apexdoc: ApexDoc = None
    source_format: Literal["sfdx", "mdapi"] = "mdapi"


class ScratchOrg(CCIBaseModel):
    config_file: Path
    days: int = None
    namespaced: str = None


class Orgs(CCIBaseModel):
    scratch: Dict[str, ScratchOrg]


class Attribute(CCIBaseModel):
    description: str
    required: bool


class Service(CCIBaseModel):
    description: str
    attributes: Dict[str, Attribute]
    validator: PythonClass = None


class CumulusCI(CCIBaseModel):
    keychain: PythonClass


class CumulusCIRoot(CCIBaseModel):
    tasks: Dict[str, Task] = {}
    flows: Dict[str, Flow] = {}
    project: Project = {}
    orgs: Orgs = {}
    services: Dict[str, Service] = {}
    cumulusci: CumulusCI = None
    plans: Dict[str, Plan] = None
    minimum_cumulusci_version: str = None


class Document(CCIBaseModel):
    __root__: CumulusCIRoot


def parse_mapping_from_yaml(source):
    return Document.parse_from_yaml(source)
