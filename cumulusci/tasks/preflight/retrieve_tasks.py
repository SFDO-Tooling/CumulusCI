from typing import List

from cumulusci.cli.runtime import CliRuntime
from cumulusci.cli.utils import group_items
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.tasks import BaseTask


class RetrieveTasks(BaseTask):
    task_options = {
        "group_name": {
            "description": "Name of the category or Group",
            "required": True,
        },
    }

    def _run_task(self):
        runtime = CliRuntime(load_keychain=True)
        tasks = runtime.get_available_tasks()
        task_groups = group_items(tasks)
        task_groups = task_groups[self.options["group_name"]]
        self.return_values: List[str] = []
        for task_name, description in task_groups:
            self.return_values.append(task_name)
        if self.return_values:
            self.return_values.sort()
        else:
            raise CumulusCIException("No tasks in the specified group")

        self.logger.info(self.return_values)
