import importlib
from typing import Optional, Type

TASK_REGISTRY = {}
TASK_FORWARD_REGISTRY = {}


def get_task_by_id(id: str) -> Optional[Type]:
    if id not in TASK_REGISTRY and id in TASK_FORWARD_REGISTRY:
        importlib.import_module(TASK_FORWARD_REGISTRY[id])

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


def forward_task(task_id: str, class_path: str):
    TASK_FORWARD_REGISTRY[task_id] = class_path


forward_task(
    "cumulusci.new_tasks.InstallPackage",
    "cumulusci.new_tasks.tasks.install_package",
)
