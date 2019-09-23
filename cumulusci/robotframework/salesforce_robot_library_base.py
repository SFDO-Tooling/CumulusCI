import logging

from cumulusci.core.config import TaskConfig
from robot.libraries.BuiltIn import BuiltIn
from cumulusci.tasks.apex.anon import AnonymousApexTask

from cumulusci.tasks.apex.batch import BatchApexWait


class SalesforceRobotLibraryBase(object):
    logger = logging.getLogger("robot_debug")
    logger.setLevel("DEBUG")

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    @property
    def salesforce(self):
        return self.builtin.get_library_instance("cumulusci.robotframework.Salesforce")

    def _run_subtask(self, taskclass, **options):
        subtask_config = TaskConfig({"options": options})
        return self.cumulusci._run_task(taskclass, subtask_config)

    def _batch_apex_wait(self, class_name):
        return self._run_subtask(BatchApexWait, class_name=class_name)

    def _run_apex(self, code):
        return self._run_subtask(AnonymousApexTask, apex=code)
