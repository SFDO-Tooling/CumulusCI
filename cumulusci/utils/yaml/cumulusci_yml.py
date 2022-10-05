"""
Pydantic models for validating cumulusci.yml

Note: If you change the model here, you should run `make schema`
to update the JSON Schema version in cumulusci.jsonschema.json
"""

import enum
from logging import getLogger
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

from pydantic import Field, root_validator, validator
from pydantic.types import DirectoryPath
from typing_extensions import Literal, TypedDict

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


class PreflightCheck(CCIDictModel):
    when: str = None
    action: str = None
    message: str = None


class Step(CCIDictModel):
    task: str = None
    flow: str = None
    ignore_failure: bool = False
    when: str = None  # is this allowed?
    options: Dict[str, Any] = VSCodeFriendlyDict
    ui_options: Dict[str, Any] = VSCodeFriendlyDict
    checks: List[PreflightCheck] = []
    description: str = None

    @root_validator()
    def _check(cls, values):
        has_task = values.get("task") and values["task"] != "None"
        has_flow = values.get("flow") and values["flow"] != "None"
        assert not (
            has_task and has_flow
        ), "Steps must have either task or flow but not both"
        return values


class Task(CCIDictModel):
    class_path: str = None
    description: str = None
    group: str = None
    # additionalProperties here works around an
    # incompatibility with VSCode's Red Hat YAML validator
    options: Dict[str, Any] = VSCodeFriendlyDict
    ui_options: Dict[str, Any] = VSCodeFriendlyDict
    name: str = None  # get rid of this???


class Flow(CCIDictModel):
    description: str = None
    steps: Dict[str, Step] = None
    group: str = None


class Package(CCIDictModel):
    name: Optional[str] = None
    name_managed: Optional[str] = None
    namespace: Optional[str] = None
    install_class: str = None
    uninstall_class: str = None
    api_version: str = None
    metadata_package_id: str = None


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
    unlocked_context: Optional[str] = None


class Plan(CCIDictModel):  # MetaDeploy plans
    title: str = None
    description: str = None
    tier: Literal["primary", "secondary", "additional"] = "primary"
    slug: str = None
    is_listed: bool = True
    steps: Dict[str, Step] = None
    checks: List[PreflightCheck] = []
    error_message: str = None
    post_install_message: str = None
    preflight_message: str = None
    allowed_org_providers: List[Literal["devhub", "user"]] = ["user"]


class DependencyResolutions(CCIDictModel):
    production: str = None
    preproduction: str = None
    resolution_strategies: Dict[str, List[str]] = None


class Project(CCIDictModel):
    name: Optional[str] = None
    package: Optional[Package] = None
    test: Optional[Test] = None
    git: Optional[Git] = None
    dependencies: Optional[List[Dict[str, str]]] = None
    dependency_resolutions: Optional[DependencyResolutions] = None
    dependency_pins: Optional[List[Dict[str, str]]]
    source_format: Literal["sfdx", "mdapi"] = "mdapi"
    custom: Optional[Dict] = None


class ScratchOrg(CCIDictModel):
    config_file: Path = None
    days: int = None
    namespaced: str = None
    setup_flow: str = None
    noancestors: bool = None


class Orgs(CCIDictModel):
    scratch: Dict[str, ScratchOrg] = None


class ServiceAttribute(CCIDictModel):
    description: str = None
    required: bool = None
    default_factory: PythonClassPath = None
    default: str = None
    sensitive: bool = False


class Service(CCIDictModel):
    description: str = None
    class_path: Optional[str]
    attributes: Dict[str, ServiceAttribute] = None
    validator: PythonClassPath = None


class CumulusCIConfig(CCIDictModel):
    keychain: PythonClassPath


class GitHubSourceRelease(str, enum.Enum):
    LATEST = "latest"
    PREVIOUS = "previous"
    LATEST_BETA = "latest_beta"


class GitHubSourceModel(HashableBaseModel):
    github: str
    resolution_strategy: Optional[str]
    commit: Optional[str]
    ref: Optional[str]
    branch: Optional[str]
    tag: Optional[str]
    release: Optional[GitHubSourceRelease]
    description: Optional[str]

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
    path: DirectoryPath


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
    plans: Dict[str, Plan] = {}
    minimum_cumulusci_version: str = None
    sources: Dict[str, Union[LocalFolderSourceModel, GitHubSourceModel]] = {}
    cli: CumulusCLIConfig = None

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
