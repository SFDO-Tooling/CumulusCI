from __future__ import unicode_literals

from cumulusci.core.config.BaseConfig import BaseConfig
from cumulusci.core.config.FlowConfig import FlowConfig
from cumulusci.core.config.TaskConfig import TaskConfig
from cumulusci.core.exceptions import TaskNotFoundError


class BaseTaskFlowConfig(BaseConfig):
    """ Base class for all configs that contain tasks and flows """

    def list_tasks(self):
        """ Returns a list of task info dictionaries with keys 'name' and 'description' """
        tasks = []
        for task in list(self.tasks.keys()):
            task_info = self.tasks[task]
            if not task_info:
                task_info = {}
            tasks.append({
                'name': task,
                'description': task_info.get('description'),
            })
        return tasks

    def get_task(self, name):
        """ Returns a TaskConfig """
        config = getattr(self, 'tasks__{}'.format(name))
        if not config:
            raise TaskNotFoundError('Task not found: {}'.format(name))
        return TaskConfig(config)

    def list_flows(self):
        """ Returns a list of flow info dictionaries with keys 'name' and 'description' """
        flows = []
        return flows

    def get_flow(self, name):
        """ Returns a FlowConfig """
        config = getattr(self, 'flows__{}'.format(name))
        return FlowConfig(config)
