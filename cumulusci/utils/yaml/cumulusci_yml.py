from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Sequence
from operator import xor

from typing_extensions import Literal, TypedDict
from pydantic import Field, root_validator

from cumulusci.utils.fileutils import DataInput, load_from_source
from cumulusci.utils.yaml.model_parser import CCIDictModel
from cumulusci.utils.yaml.safer_loader import load_yaml_data

default_logger = getLogger(__name__)


#  type aliases
PythonClassPath = str
URL = str


class Step(CCIDictModel):
    task: str = None
    flow: str = None
    options: Dict[str, Any] = {}
    ignore_failure: bool = False
    when: str = None  # is this allowed?
    ui_options: Dict[str, Any] = {}

    @root_validator()
    def _check(cls, values):
        assert xor(
            bool(values.get("task")), bool(values.get("flow"))
        ), "Steps must have a task or flow"
        return values


class Task(CCIDictModel):
    name: str = None  # get rid of this???
    class_path: str = None  # to discuss
    description: str = None
    options: Dict[str, Any] = None
    group: str = None
    ui_options: Dict[str, Any] = None


class Flow(CCIDictModel):
    description: str = None
    steps: Dict[str, Step]
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


class ReleaseNotesParser(CCIDictModel):
    class_path: PythonClassPath
    title: str


class ReleaseNotes(CCIDictModel):
    parsers: Dict[int, ReleaseNotesParser]


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


class PreflightCheck(CCIDictModel):
    when: str = None
    action: str = None
    message: str = None


class Plan(CCIDictModel):  # MetaDeploy plans
    title: str
    description: str = None
    tier: str = Literal["primary", "secondary", "additional"]
    slug: str
    is_listed: bool = True
    steps: Dict[str, Step]
    checks: List[PreflightCheck] = []
    group: str = None
    error_message: str = None
    post_install_message: str = None
    preflight_message: str = None


class Project(CCIDictModel):
    name: str = None
    package: Package = None
    test: Test = None
    git: Git = None
    dependencies: List[Dict[str, URL]] = None  # TODO
    source_format: Literal["sfdx", "mdapi"] = "mdapi"


class ScratchOrg(CCIDictModel):
    config_file: Path
    days: int = None
    namespaced: str = None
    setup_flow: str = None


class Orgs(CCIDictModel):
    scratch: Dict[str, ScratchOrg]


class ServiceAttribute(CCIDictModel):
    description: str
    required: bool


class Service(CCIDictModel):
    description: str
    attributes: Dict[str, ServiceAttribute]
    validator: PythonClassPath = None


class CumulusCIConfig(CCIDictModel):
    keychain: PythonClassPath


class Source(CCIDictModel):
    github: URL = None
    release: Literal["latest", "previous", "latest_beta"] = None
    ref: str = None
    branch: str = None
    tag: str = None


class CumulusCLIConfig(CCIDictModel):
    show_stacktraces: bool = False
    plain_output: bool = None


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
    cli: CumulusCLIConfig = None


class CumulusCIFile(CCIDictModel):
    __root__: Union[CumulusCIRoot, None]


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


class ErrorDict(TypedDict):
    "The structure of a Pydantic error dictionary. Google TypedDict if its new to you."
    loc: Sequence[Union[str, int]]
    msg: str
    type: str


def _log_yaml_error(logger, error: ErrorDict):
    "Format and log a Pydantic-style error dictionary"
    logger.warning("CumulusCI Parsing Error:")
    loc = " -> ".join(repr(x) for x in error["loc"] if x != "__root__")
    logger.warning("%s : %s", loc, error["msg"])
    logger.error(
        "NOTE: These errors will cause major problems in future versions of CumulusCI."
    )
    logger.error(
        "If you think your YAML has no error, please report the bug to the CumulusCI team."
    )
    logger.error("https://github.com/SFDO-Tooling/CumulusCI/issues/")


def cci_safe_load(
    source: DataInput, context: str = None, on_error: callable = None, logger=None
):
    """Load a CumulusCI.yml file and issue warnings for unknown structures."""

    assert not (
        on_error and logger
    ), "Please specify either on_error or logger but not both"
    on_error = on_error or (lambda error: _log_yaml_error(logger, error))

    logger = logger or default_logger

    with load_from_source(source) as (data_stream, filename):
        data = load_yaml_data(data_stream, filename)
        context = context or filename

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


# validate YML files as a CLI for smoke testing
if __name__ == "__main__":
    import sys
    from glob import glob
    from pprint import pprint

    def main():
        "Validate YML files from CLI for smoke testing"

        globs = sys.argv[1:]
        errors = []
        for g in globs:
            filenames = glob(g)
            for filename in filenames:
                print("Validating", filename)

                cci_safe_load(filename, filename, logger=getLogger(__name__))
        pprint(errors)

    main()
