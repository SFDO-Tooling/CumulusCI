""" Tests for the SFDX Command Wrapper"""

from unittest import mock
import unittest

from unittest.mock import MagicMock
from unittest.mock import patch

from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggerMixin

from cumulusci.tasks.command import CommandException
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.tasks.sfdx import SFDXOrgTask
from cumulusci.tasks.sfdx import SFDXJsonTask


class TestSFDXBaseTask(MockLoggerMixin, unittest.TestCase):
    """ Tests for the Base Task type """

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(
            self.global_config, config={"noyaml": True}
        )
        self.task_config = TaskConfig()

        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_base_task(self):
        """ The command is prefixed w/ sfdx """

        self.task_config.config["options"] = {"command": "force:org", "extra": "--help"}
        task = SFDXBaseTask(self.project_config, self.task_config)

        try:
            task()
        except CommandException:
            pass

        self.assertEqual("sfdx force:org --help", task.options["command"])

    @patch(
        "cumulusci.tasks.sfdx.SFDXOrgTask._update_credentials",
        MagicMock(return_value=None),
    )
    @patch("cumulusci.tasks.command.Command._run_task", MagicMock(return_value=None))
    def test_keychain_org_creds(self):
        """ Keychain org creds are passed by env var """

        self.task_config.config["options"] = {"command": "force:org --help"}
        access_token = "00d123"
        org_config = OrgConfig(
            {
                "access_token": access_token,
                "instance_url": "https://test.salesforce.com",
            },
            "test",
        )

        task = SFDXOrgTask(self.project_config, self.task_config, org_config)

        try:
            task()
        except CommandException:
            pass

        self.assertIn("SFDX_INSTANCE_URL", task._get_env())
        self.assertIn("SFDX_DEFAULTUSERNAME", task._get_env())
        self.assertIn(access_token, task._get_env()["SFDX_DEFAULTUSERNAME"])

    def test_scratch_org_username(self):
        """ Scratch Org credentials are passed by -u flag """
        self.task_config.config["options"] = {"command": "force:org --help"}
        org_config = ScratchOrgConfig({"username": "test@example.com"}, "test")

        task = SFDXOrgTask(self.project_config, self.task_config, org_config)
        self.assertIn("-u test@example.com", task.options["command"])


class TestSFDXJsonTask(unittest.TestCase):
    def test_get_command(self):
        task = create_task(SFDXJsonTask)
        command = task._get_command()
        self.assertEqual("sfdx force:mdapi:deploy --json", command)

    def test_process_output(self):
        task = create_task(SFDXJsonTask)
        task.logger = mock.Mock()
        task._process_output("{}")
        task.logger.info.assert_called_once_with("JSON = {}")

    def test_process_output__json_parse_error(self):
        task = create_task(SFDXJsonTask)
        task.logger = mock.Mock()
        task._process_output("{")
        task.logger.error.assert_called_once()
