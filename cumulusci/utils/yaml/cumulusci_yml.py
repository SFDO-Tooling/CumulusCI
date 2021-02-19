import re
from io import StringIO
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Sequence

from typing_extensions import Literal, TypedDict
from pydantic import Field
from yaml import safe_load

from cumulusci.utils.fileutils import DataInput, load_from_source
from cumulusci.utils.yaml.model_parser import CCIDictModel

default_logger = getLogger(__name__)


NBSP = "\u00A0"

pattern = re.compile(r"^\s*[\u00A0]+\s*", re.MULTILINE)


#  type aliases
PythonClassPath = str
URL = str


class FlowReference(CCIDictModel):
    flow: str = None
    options: Dict[str, Any] = {}
    ignore_failure: bool = None  # is this allowed?
    when: str = None  # is this allowed?
    ui_options: Dict[str, Any] = {}


class TaskReference(CCIDictModel):
    task: str
    options: Dict[str, Any] = {}
    ui_options: Dict[str, Any] = {}
    ignore_failure: bool = None
    when: str = None  # is this a documented feature?
    # classpath, description allowed?


class Task(CCIDictModel):
    name: str = None  # is this real or a typo
    class_path: str = None
    description: str = None
    options: Dict[str, Any] = None
    group: str = None
    ui_options: Dict[str, Any] = None


class Flow(CCIDictModel):
    description: str = None
    steps: Dict[str, Union[FlowReference, TaskReference]]
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
    class_path: PythonClassPath
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
    two_gp_context: str = Field(None, alias="2gp_context")


class ApexDoc(CCIDictModel):
    homepage: str = None  # can't find these in the CCI Python code
    banner: str = None
    branch: str = None
    repo_dir: Path = None


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
    steps: Dict[str, Union[FlowReference, TaskReference]]
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
    validator: PythonClassPath = None


class CumulusCIConfig(CCIDictModel):
    keychain: PythonClassPath


class Source(CCIDictModel):
    github: URL = None
    release: str = None


class CumulusCIRoot(CCIDictModel):
    tasks: Dict[str, Task] = {}
    flows: Dict[str, Flow] = {}
    project: Project = {}
    orgs: Orgs = {}
    services: Dict[str, Service] = {}
    cumulusci: CumulusCIConfig = None
    plans: Dict[str, Plan] = []
    minimum_cumulusci_version: str = None
    sources: Dict[str, Source] = []


class CumulusCIFile(CCIDictModel):
    __root__: CumulusCIRoot


def parse_from_yaml(source):
    "Parse from a path, url, path-like or file-like"
    return CumulusCIFile.parse_from_yaml(source)


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


def _replace_nbsp(origdata, filename, logger=default_logger):
    "Replace nbsp characters in leading whitespace in a YAML file."
    counter = 0

    def _replacer_func(matchobj):
        nonlocal counter
        counter += 1
        string = matchobj.group(0)
        rc = string.replace(NBSP, " ")
        return rc

    data = pattern.sub(_replacer_func, origdata)

    if counter:
        plural = "s were" if counter > 1 else " was"
        logger.warning(
            f"Note: {counter} lines with non-breaking space character{plural} detected in {filename}.\n"
            "Perhaps you cut and pasted from a Web page?\n"
            "Future versions of CumulusCI may disallow these characters.\n"
        )
    return data


class ErrorDict(TypedDict):
    "The structure of a Pydantic error dictionary. Google TypedDict if its new to you."
    loc: Sequence[Union[str, int]]
    msg: str
    type: str


def _log_yaml_error(logger, error: ErrorDict):
    "Format and log a Pydantic-style error dictionary"
    logger.warning("CumulusCI Parsing Error:")
    loc = " -> ".join((repr(x) for x in error["loc"]))
    logger.warning("%s : %s", loc, error["msg"])


def cci_safe_load(
    source: DataInput, context: str = None, on_error: callable = None, logger=None
):
    """Load a CumulusCI.yml file and issue warnings for unknown structures."""

    assert not (
        on_error and logger
    ), "Please specify either on_error or logger but not both"

    logger = logger or default_logger

    with load_from_source(source) as (filename, data_stream):
        # this is inelegant but the _replace_nbsp code is a lot easier
        # to write with regexps and Python regexps don't work with streams
        cleaned_up_data = _replace_nbsp(data_stream.read(), data_stream, logger)
        data = safe_load(StringIO(cleaned_up_data))
        context = context or filename

        on_error = on_error or (lambda error: _log_yaml_error(logger, error))

        try:
            validate_data(data, context=context, on_error=on_error)
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
        return data
