import functools
import itertools
import typing as T
from inspect import signature

import pydantic
from pydantic import BaseModel

from cumulusci.core.config import BaseProjectConfig, OrgConfig, TaskConfig
from cumulusci.core.exceptions import CumulusCIException, TaskOptionsError
from cumulusci.new_tasks import fixtures


class DynamicOptionsProtocol(T.Protocol):
    def freeze(self, *args):
        ...


class TaskSpec(BaseModel):
    options_models: T.List[T.Type[BaseModel]]
    dynamic_options_models: T.List[
        T.Type[BaseModel]
    ]  # TODO: constraint to DynamicOptionsProtocol
    return_model: T.Optional[T.Type[BaseModel]] = None
    task_id: str
    idempotent: bool
    name: str


class TaskProtocol(T.Protocol):
    task_spec: T.ClassVar[TaskSpec]

    # TODO: constrain options to specified options types
    def __init__(self, options: T.Any):
        ...

    def run(self, *args) -> T.Any:
        ...


G = T.TypeVar("G")


def call_with_fixtures(
    function: T.Callable[..., G], org: OrgConfig, project: BaseProjectConfig
) -> G:
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
    nt: T.Type[TaskProtocol],
    task_config: TaskConfig,
    org: OrgConfig,
    project: BaseProjectConfig,
) -> T.Any:
    # Validate options

    input_options = task_config.config["options"]
    options = None
    # Attempt to initialize with dynamic options classes
    # If we succeed, freeze the options.
    for options_class in nt.task_spec.dynamic_options_models:
        try:
            options = options_class.parse_obj(input_options)
        except pydantic.ValidationError:
            pass
        else:
            options = call_with_fixtures(options.freeze, org, project)
            assert type(options) in nt.task_spec.options_models
            break

    # Attempt to initialize with frozen options classes
    if options is None:
        for options_class in nt.task_spec.options_models:
            try:
                options = options_class.parse_obj(input_options)
            except pydantic.ValidationError:
                pass

    if options is None:
        raise TaskOptionsError("Unable to parse options for task")

    task = nt(options)
    return task


def run_constructed_newtask(
    nt: T.Type[TaskProtocol], org: OrgConfig, project: BaseProjectConfig
) -> T.Any:
    return call_with_fixtures(nt.run, org, project)


def run_newtask(
    nt: T.Type[TaskProtocol],
    task_config: TaskConfig,
    org: OrgConfig,
    project: BaseProjectConfig,
) -> T.Any:

    return run_constructed_newtask(
        construct_newtask(nt, task_config, org, project), org, project
    )


def get_newtask_options(klass: T.Type[TaskProtocol]) -> dict:
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
                    klass.task_spec.dynamic_options_models,
                    klass.task_spec.options_models,
                ),
            )
        ),
        {},
    )


def get_newtask_needs_org(klass: T.Type[TaskProtocol]) -> bool:
    """Returns whether the task's `run()` method or any dynamic option
    class' `freeze()` method requires the `org` fixture."""
    return (
        any(
            "org" in signature(d.freeze).parameters
            for d in klass.task_spec.dynamic_options_models
        )
        or "org" in signature(klass.run).parameters
    )
