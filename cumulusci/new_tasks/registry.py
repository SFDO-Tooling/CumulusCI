import importlib
import typing as T

from cumulusci.new_tasks.new_tasks import TaskProtocol

TASK_REGISTRY = {}
TASK_FORWARD_REGISTRY = {}


def get_task_by_id(id: str) -> T.Optional[T.Type[TaskProtocol]]:
    if id not in TASK_REGISTRY and id in TASK_FORWARD_REGISTRY:
        importlib.import_module(TASK_FORWARD_REGISTRY[id])

    return TASK_REGISTRY.get(id)


def task(klass: T.Type[TaskProtocol]):

    TASK_REGISTRY[klass.task_spec.task_id] = klass


def forward_task(task_id: str, class_path: str):
    TASK_FORWARD_REGISTRY[task_id] = class_path


forward_task(
    "cumulusci.new_tasks.InstallPackage",
    "cumulusci.new_tasks.tasks.install_package",
)
