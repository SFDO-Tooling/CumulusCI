from unittest import mock
import unittest

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig

# from cumulusci.tasks.salesforce import ActivateFlowProcesses
from .util import create_task


class TestActivateFlowProcesses(unittest.TestCase):
    @mock.patch("cumulusci.tasks.salesforce.ActivateFlowProcesses")
    def test_activate_flow_processes(self, ActivateFlowProcesses):
        project_config = BaseProjectConfig(
            BaseGlobalConfig(),
            {"project": {"package": {"name": "TestPackage", "api_version": "43.0"}}},
        )
        task = create_task(ActivateFlowProcesses, project_config=project_config)
        task._get_ActivateFlowProcesses()
        ActivateFlowProcesses.assert_called()
