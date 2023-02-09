from difflib import get_close_matches
from typing import Mapping, MutableMapping

from cumulusci.core.exceptions import ConfigError
from cumulusci.core.utils import merge_configs


def merge_cumulus_config(configs: Mapping):
    config = merge_configs(configs)
    merge_task_extensions(config.get("tasks", {}))
    return config


def merge_task_extensions(tasks: Mapping):
    for taskname, task in tasks.items():
        if task.get("extends"):
            merge_task_extension(taskname, task, tasks, set())


def merge_task_extension(
    taskname: str, task: MutableMapping, tasks: Mapping, stack: set
):
    # the stack is because this function calls itself recursively
    # and I want to detect a recursion cycle faster than Python would
    if taskname in stack:
        trace = " -> ".join(stack)
        raise ConfigError(
            f"Circular references detected in `extends` relationships {trace}"
        )
    stack = set(stack)
    stack.add(taskname)

    base_task_name = task.get("extends")
    if base_task_name is None:
        return

    if base_task_name == taskname:
        if taskname in tasks:
            error = f"{taskname} does not need to extend itself. You can override a task definition without the extends keyword."
        else:
            error = f"{taskname} cannot extend {taskname} because no previous definition exists, and tasks need not use the extend keyword to override task definitions."
        raise ConfigError(error)

    assert isinstance(base_task_name, str)

    other_task: dict = tasks.get(base_task_name, {})
    if not other_task:
        match_list = get_close_matches(base_task_name, tasks.keys(), n=1)
        error = f"Cannot find task named `{base_task_name}`."
        if match_list:
            error += f" Did you mean `{match_list[0]}`?"
        raise ConfigError(error)

    other_class_path = other_task.get("class_path")
    if not other_class_path:
        merge_task_extension(base_task_name, other_task, tasks, stack)
        other_class_path = other_task.get("class_path")

    if not other_class_path:
        raise ConfigError(f"Cannot find `class_path` for `{base_task_name}`")

    task["class_path"] = other_class_path
