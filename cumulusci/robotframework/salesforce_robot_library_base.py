import logging

from cumulusci.core.config import TaskConfig
from robot.libraries.BuiltIn import BuiltIn
from cumulusci.tasks.apex.anon import AnonymousApexTask

from cumulusci.tasks.apex.batch import BatchApexWait


class SalesforceRobotLibraryBase(object):
    """Base class for any Robot Keyword Library which needs access to
       Salesforce and CumulusCI features."""

    logger = logging.getLogger("robot_debug")
    logger.setLevel("DEBUG")

    @property
    def builtin(self):
        return BuiltIn()

    @property
    def cumulusci(self):
        """Get access to the CumulusCI Keyword Library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.CumulusCI")

    @property
    def salesforce(self):
        """Get access to the Salesforce Keyword Library"""
        return self.builtin.get_library_instance("cumulusci.robotframework.Salesforce")

    def _run_subtask(self, taskclass, **options):
        """Helper method for running CCI tasks"""
        subtask_config = TaskConfig({"options": options})
        return self.cumulusci._run_task(taskclass, subtask_config)

    def _batch_apex_wait(self, class_name):
        """Helper method for waiting for Salesforce jobs to end"""
        return self._run_subtask(BatchApexWait, class_name=class_name)

    def _run_apex(self, code):
        """Helper method for running Apex code easily"""
        return self._run_subtask(AnonymousApexTask, apex=code)
