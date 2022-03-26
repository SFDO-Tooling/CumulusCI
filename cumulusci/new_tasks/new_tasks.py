import functools
import itertools
from inspect import signature
from typing import Any, Callable, Type

import pydantic

from cumulusci.core.config import BaseProjectConfig, OrgConfig, TaskConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.new_tasks import fixtures


def call_with_fixtures(
    function: Callable, org: OrgConfig, project: BaseProjectConfig
) -> Any:
    sig = signature(function)

    # Inject fixtures
    parameters = []
    for name in sig.parameters:
        if hasattr(fixtures, name):
            parameters.append(getattr(fixtures, name)(org, project))
        else:
            raise CumulusCIException(f"Invalid task fixture: {name}")

    return function(*parameters)


def construct_newtask(
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
    return task


def run_constructed_newtask(nt: Any, org: OrgConfig, project: BaseProjectConfig) -> Any:
    return call_with_fixtures(nt.run, org, project)


def run_newtask(
    nt: Type, task_config: TaskConfig, org: OrgConfig, project: BaseProjectConfig
) -> Any:

    return run_constructed_newtask(
        construct_newtask(nt, task_config, org, project), org, project
    )


def get_newtask_options(klass: Type) -> dict:
    # NOTE: the CLI does not enforce the `required` parameter
    # This is enforced via Pydantic itself.

    return functools.reduce(
        lambda a, b: a | b,
        (
            {
                k: {
                    "description": v.get("description") or "no description",
                    "required": k in schema.get("required", []),
                }
                for k, v in schema.items()
            }
            for schema in map(
                lambda m: m.schema()["properties"],
                itertools.chain(
                    klass.Meta.dynamic_options_models, klass.Meta.options_models
                ),
            )
        ),
        {},
    )


def get_newtask_needs_org(klass: Type) -> bool:
    """Returns whether the task's `run()` method or any dynamic option
    class' `freeze()` method requires the `org` fixture."""
    return (
        any(
            "org" in signature(d.freeze).parameters
            for d in klass.Meta.dynamic_options_models
        )
        or "org" in signature(klass.run).parameters
    )
