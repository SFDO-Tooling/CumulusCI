from __future__ import unicode_literals

from cumulusci.core.config import BaseConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import TaskNotFoundError, FlowNotFoundError


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
        config = getattr(self, "tasks__{}".format(name))
        if not config:
            raise TaskNotFoundError("Task not found: {}".format(name))
        return TaskConfig(config)

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        return list_infos(self.flows)

    def get_flow(self, name):
        """ Returns a FlowConfig """
        config = getattr(self, "flows__{}".format(name))
        if not config:
            raise FlowNotFoundError("Flow not found: {}".format(name))
        return FlowConfig(config)
