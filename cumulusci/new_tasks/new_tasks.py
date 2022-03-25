import logging
from inspect import signature
from typing import Any, Callable, Optional, Type

import pydantic

from cumulusci.core.config import BaseProjectConfig, OrgConfig, TaskConfig
from cumulusci.core.exceptions import TaskOptionsError

ALL_FIXTURES = ["repo", "logger", "org", "project"]


def get_fixture(fixture: str, org: OrgConfig, project: BaseProjectConfig) -> Any:
    if fixture == "repo":
        return project.get_repo()
    elif fixture == "logger":
        return logging.getLogger(__name__)
    elif fixture == "org":
        return org
    elif fixture == "project":
        return project


def call_with_fixtures(
    function: Callable, org: OrgConfig, project: BaseProjectConfig
) -> Any:
    sig = signature(function)

    # Inject fixtures
    parameters = []
    for name in sig.parameters:
        if name in ALL_FIXTURES:
            parameters.append(get_fixture(name, org, project))

    return function(*parameters)


def run_newtask(
    nt: Type, task_config: TaskConfig, org: OrgConfig, project: BaseProjectConfig
) -> Any:
    # Validate options

    input_options = task_config.config["options"]
    options = None
    # Attempt to initialize with dynamic options classes
    # If we succeed, freeze the options.
    for options_class in nt.Meta.dynamic_options_models:
        try:
            options = options_class.parse_obj(input_options)
        except pydantic.ValidationError:
            pass
        else:
            options = call_with_fixtures(options.freeze, org, project)
            assert type(options) in nt.Meta.options_models
            break

    # Attempt to initialize with frozen options classes
    if options is None:
        for options_class in nt.Meta.options_models:
            try:
                options = options_class.parse_obj(input_options)
            except pydantic.ValidationError:
                pass

    if options is None:
        raise TaskOptionsError("Unable to parse options for task")

    task = nt(options)
    return call_with_fixtures(task.run, org, project)


TASK_REGISTRY = {}


def get_task_by_id(id: str) -> Optional[Type]:
    return TASK_REGISTRY.get(id)


REQUIRED_KEYS = (
    "task_id",
    "options_models",
    "dynamic_options_models",
    "return_model",
    "idempotent",
    "name",
)


def task(klass: Type):

    assert hasattr(klass, "Meta")
    for k in REQUIRED_KEYS:
        assert hasattr(klass.Meta, k)

    TASK_REGISTRY[klass.Meta.task_id] = klass
