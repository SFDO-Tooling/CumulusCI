from difflib import get_close_matches

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import FlowNotFoundError


def list_infos(infos):
    rv = []
    for info_name in infos:
        info = infos[info_name]
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
    """ Base class for all configs that contain tasks and flows """

    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """
        return list_infos(self.tasks)

    def get_task(self, name):
        """ Returns a TaskConfig """
        config = getattr(self, f"tasks__{name}")
        if not config:
            error_msg = f"Task not found: {name}"
            suggestion = self.get_suggested_name(name, self.tasks)
            raise TaskNotFoundError(error_msg + suggestion)
        return TaskConfig(config)

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        return list_infos(self.flows)

    def get_flow(self, name):
        """ Returns a FlowConfig """
        config = getattr(self, f"flows__{name}")
        if not config:
            error_msg = f"Flow not found: {name}"
            suggestion = self.get_suggested_name(name, self.flows)
            raise FlowNotFoundError(error_msg + suggestion)
        return FlowConfig(config)

    def get_suggested_name(self, name, steps):
        """
        Given a name that cannot be resolved and a list of tasks/flow dicts, returns the nearest match.
        """
        match_list = get_close_matches(name, steps.keys(), n=1)
        if match_list:
            return f'. Did you mean "{match_list[0]}"?'
        else:
            return ""
