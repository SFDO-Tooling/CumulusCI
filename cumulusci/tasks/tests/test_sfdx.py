""" Tests for the SFDX Command Wrapper"""


from unittest import mock
from unittest.mock import MagicMock, patch

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    ScratchOrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.command import CommandException
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.sfdx import SFDXBaseTask, SFDXJsonTask, SFDXOrgTask


class TestSFDXBaseTask(MockLoggerMixin):
    """Tests for the Base Task type"""

    def setup_method(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.task_config = TaskConfig()

        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_base_task(self):
        """The command is prefixed w/ sfdx"""

        self.task_config.config["options"] = {"command": "force:org", "extra": "--help"}
        task = SFDXBaseTask(self.project_config, self.task_config)

        try:
            task()
        except CommandException:
            pass

        assert task.options["command"] == "force:org"
        assert task._get_command() == "sfdx force:org --help"

    @patch("cumulusci.tasks.command.Command._run_task", MagicMock(return_value=None))
    def test_keychain_org_creds(self):
        """Keychain org creds are passed by env var"""

        self.task_config.config["options"] = {"command": "force:org --help"}
        access_token = "00d123"
        org_config = OrgConfig(
            {
                "instance_url": "https://test.salesforce.com",
            },
            "test",
        )

        def refresh_oauth_token(keychain):
            org_config.config["access_token"] = access_token

        org_config.refresh_oauth_token = mock.Mock(side_effect=refresh_oauth_token)
        org_config.save = mock.Mock()

        task = SFDXOrgTask(self.project_config, self.task_config, org_config)
        task()

        org_config.refresh_oauth_token.assert_called_once()
        assert "SFDX_INSTANCE_URL" in task._get_env()
        assert "SFDX_DEFAULTUSERNAME" in task._get_env()
        assert access_token in task._get_env()["SFDX_DEFAULTUSERNAME"]

    def test_scratch_org_username(self):
        """Scratch Org credentials are passed by -u flag"""
        self.task_config.config["options"] = {"command": "force:org --help"}
        org_config = ScratchOrgConfig({"username": "test@example.com"}, "test")

        task = SFDXOrgTask(self.project_config, self.task_config, org_config)
        assert "-u test@example.com" in task._get_command()


class TestSFDXJsonTask:
    def test_get_command(self):
        task = create_task(SFDXJsonTask)
        command = task._get_command()
        assert command == "sfdx force:mdapi:deploy --json"

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
