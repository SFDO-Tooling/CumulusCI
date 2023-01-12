""" Tests for the Command tasks """


from io import BytesIO
from unittest import mock

import pytest
from sarge import Capture

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.command import Command, CommandException, SalesforceCommand


class TestCommandTask(MockLoggerMixin):
    """Tests for the basic command task"""

    def setup_method(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_functional_run_ls(self):
        """Functional test that actually subprocesses and runs command.

        Checks that command either ran successfully or failed as expected
        so that it can be run on any platform. Other tests will mock
        the subprocess interaction.
        """

        self.task_config.config["options"] = {"command": "ls -la"}

        task = Command(self.project_config, self.task_config)

        # try to run the command and handle the command Exception
        # if no exception, confirm that we logged
        # if exception, confirm exception matches expectations
        try:
            task()
        except CommandException:
            assert any("Return code" in s for s in self.task_log["error"])

        assert any("total" in s for s in self.task_log["info"])

    def test_return_values_success(self):
        """Verify return_values is set when command succeeds"""
        self.task_config.config["options"] = {"command": "ls"}
        task = Command(self.project_config, self.task_config)
        task()
        assert task.return_values == {"returncode": 0}

    def test_return_values_exception(self):
        """Verify return_values is set when command fails"""
        self.task_config.config["options"] = {"command": "exit 1"}
        task = Command(self.project_config, self.task_config)
        with pytest.raises(CommandException):
            task()
        assert task.return_values == {"returncode": 1}

    def test_init__json_env(self):
        task_config = TaskConfig({"options": {"env": "{}", "command": "ls"}})
        task = Command(self.project_config, task_config)
        assert {} == task.options["env"]

    def test_init__dict_env(self):
        task_config = TaskConfig({"options": {"env": {}, "command": "ls"}})
        task = Command(self.project_config, task_config)
        assert {} == task.options["env"]

    def test_get_env__pass_env_false(self):
        task_config = TaskConfig({"options": {"pass_env": "False", "command": "ls"}})
        task = Command(self.project_config, task_config)
        assert {} == task._get_env()

    def test_handle_returncode(self):
        task_config = TaskConfig({"options": {"command": "ls"}})
        task = Command(self.project_config, task_config)
        with pytest.raises(CommandException):
            task._handle_returncode(1, BytesIO(b"err"))

    @mock.patch("cumulusci.tasks.command.sarge")
    def test_run_task(self, sarge):
        p = mock.Mock()
        p.returncode = 0
        p.stdout = Capture()
        p.stdout.add_stream(BytesIO(b"testing testing 123"))
        p.stderr = Capture()
        p.stderr.add_stream(BytesIO(b"e"))
        sarge.Command.return_value = p

        self.task_config.config["options"] = {"command": "ls -la"}
        task = Command(self.project_config, self.task_config)
        task()

        assert any("testing testing" in s for s in self.task_log["info"])


class TestSalesforceCommand:
    def setup_method(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.task_config = TaskConfig({"options": {"command": "ls"}})
        self.org_config = OrgConfig(
            {"access_token": "TOKEN", "instance_url": "https://na01.salesforce.com"},
            "test",
        )
        self.org_config.refresh_oauth_token = mock.Mock()

    def test_update_credentials(self):
        task = SalesforceCommand(self.project_config, self.task_config, self.org_config)
        task()
        self.org_config.refresh_oauth_token.assert_called_once()

    def test_get_env(self):
        task = SalesforceCommand(self.project_config, self.task_config, self.org_config)
        env = task._get_env()
        assert "SF_ACCESS_TOKEN" in env
        assert "SF_INSTANCE_URL" in env
