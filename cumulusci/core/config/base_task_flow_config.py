from difflib import get_close_matches
from typing import Any, Dict, List

from cumulusci.core.config import BaseConfig, FlowConfig, TaskConfig
from cumulusci.core.exceptions import (
    CumulusCIException,
    FlowNotFoundError,
    TaskNotFoundError,
)


def list_infos(infos: dict) -> List[Dict[str, str]]:
    rv = []
    for info_name, info in infos.items():
        if not info:
            info = {}
        rv.append(
            {
                "name": info_name,
                "description": info.get("description", ""),
                "group": info.get("group"),
            }
        )

    return rv


class BaseTaskFlowConfig(BaseConfig):
    """Base class for all configs that contain tasks and flows"""

    tasks: dict
    flows: dict

    def list_tasks(self) -> List[Dict[str, str]]:
        """Returns a list of task info dictionaries with keys 'name' and 'description'"""
        return list_infos(self.tasks)

    def get_task(self, name: str) -> TaskConfig:
        """Returns a TaskConfig"""
        config = self.lookup(f"tasks__{name}")
        if not config and name not in self.tasks:
            # task does not exist
            error_msg = f"Task not found: {name}"
            suggestion = self.get_suggested_name(name, self.tasks)
            raise TaskNotFoundError(error_msg + suggestion)
        elif not config:
            # task exists but there is no config at all
            error_msg = f"No configuration found for task: {name}"
            raise CumulusCIException(error_msg)
        elif "class_path" not in config:
            # task exists and there is a config but it has no class_path defined and it is not a base task override
            error_msg = f"Task has no class_path defined: {name}"
            raise CumulusCIException(error_msg)

        return TaskConfig(config)

    def list_flows(self) -> List[Dict[str, str]]:
        """Returns a list of flow info dictionaries with keys 'name' and 'description'"""
        return list_infos(self.flows)

    def get_flow(self, name: str) -> FlowConfig:
        """Returns a FlowConfig"""
        config = self.lookup(f"flows__{name}")
        if not config:
            error_msg = f"Flow not found: {name}"
            suggestion = self.get_suggested_name(name, self.flows)
            raise FlowNotFoundError(error_msg + suggestion)
        return FlowConfig(config)

    def get_suggested_name(self, name: str, steps: Dict[str, Any]) -> str:
        """
        Given a name that cannot be resolved and a list of tasks/flow dicts, returns the nearest match.
        """
        match_list = get_close_matches(name, steps.keys(), n=1)
        if match_list:
            return f'. Did you mean "{match_list[0]}"?'
        else:
            return ""
