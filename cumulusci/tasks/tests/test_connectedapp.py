""" Tests for the connectedapp tasks """

import os
import re
from unittest import mock

import pytest

try:
    from json.decoder import JSONDecodeError
except ImportError:
    JSONDecodeError = ValueError
from unittest.mock import MagicMock

from cumulusci.core.config import (
    BaseProjectConfig,
    ServiceConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.keychain import DEFAULT_CONNECTED_APP, BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.tasks.connectedapp import CreateConnectedApp
from cumulusci.utils import temporary_dir


class TestCreateConnectedApp(MockLoggerMixin):
    """Tests for the CreateConnectedApp task"""

    def setup_method(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )

        keychain = BaseProjectKeychain(self.project_config, "")
        self.project_config.set_keychain(keychain)

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages
        self.label = "Test_Label"
        self.username = "TestUser@Name"
        self.email = "TestUser@Email"
        self.task_config = TaskConfig(
            {
                "options": {
                    "label": self.label,
                    "username": self.username,
                    "email": self.email,
                }
            }
        )

    def test_init_options(self):
        """Passed options are correctly initialized"""
        self.task_config.config["options"]["connect"] = True
        self.task_config.config["options"]["overwrite"] = True
        task = CreateConnectedApp(self.project_config, self.task_config)
        assert task.options["label"] == self.label
        assert task.options["username"] == self.username
        assert task.options["email"] == self.email
        assert task.options["connect"] is True
        assert task.options["overwrite"] is True

    def test_init_options_invalid_label(self):
        """Non-alphanumeric + _ label raises TaskOptionsError"""
        self.task_config.config["options"]["label"] = "Test Label"
        with pytest.raises(TaskOptionsError, match="^label value must contain only"):
            CreateConnectedApp(self.project_config, self.task_config)

    def test_init_options_email_default(self):
        """email option defaults to email from github service"""
        del self.task_config.config["options"]["email"]
        self.project_config.config["services"] = {
            "github": {"attributes": {"email": {}}}
        }
        self.project_config.keychain.set_service(
            "github", "test_alias", ServiceConfig({"email": self.email})
        )
        task = CreateConnectedApp(self.project_config, self.task_config)
        assert task.options["email"] == self.email

    def test_init_options_email_not_found(self):
        """TaskOptionsError is raised if no email provided and no github service exists"""
        del self.task_config.config["options"]["email"]
        self.project_config.config["services"] = {"github": {"attributes": {}}}
        with pytest.raises(TaskOptionsError, match="github"):
            CreateConnectedApp(self.project_config, self.task_config)

    @mock.patch("cumulusci.tasks.connectedapp.CreateConnectedApp._run_command")
    def test_get_command(self, run_command_mock):
        del self.task_config.config["options"]["username"]
        task = CreateConnectedApp(self.project_config, self.task_config)
        run_command_mock.side_effect = lambda **kw: kw["output_handler"](
            b'{"result":[{"value":"username"}]}'
        )
        task.tempdir = "asdf"
        command = task._get_command()
        assert (
            command
            == "sf project deploy start --wait 5 -o username --metadata-dir asdf"
        )

    def test_process_json_output(self):
        """_process_json_output returns valid json"""
        task = CreateConnectedApp(self.project_config, self.task_config)
        output = task._process_json_output('{"foo":"bar"}')
        assert output == {"foo": "bar"}

    def test_process_json_output_invalid(self):
        """_process_json_output with invalid input logs output and raises JSONDecodeError"""
        task = CreateConnectedApp(self.project_config, self.task_config)
        with pytest.raises(JSONDecodeError):
            task._process_json_output("invalid")
        assert self.task_log["error"] == ["Failed to parse json from output: invalid"]

    @mock.patch(
        "cumulusci.tasks.connectedapp.CreateConnectedApp._set_default_username",
        MagicMock(return_value=None),
    )
    def test_process_devhub_output(self):
        """username is parsed from json response"""
        del self.task_config.config["options"]["username"]
        task = CreateConnectedApp(self.project_config, self.task_config)
        task._process_devhub_output('{"result":[{"value":"' + self.username + '"}]}')
        assert task.options.get("username") == self.username

    @mock.patch(
        "cumulusci.tasks.connectedapp.CreateConnectedApp._set_default_username",
        MagicMock(return_value=None),
    )
    def test_process_devhub_output_not_configured(self):
        """TaskOptionsError is raised if no username provided and no default found"""
        del self.task_config.config["options"]["username"]
        task = CreateConnectedApp(self.project_config, self.task_config)
        with pytest.raises(TaskOptionsError, match="^No sfdx config found"):
            task._process_devhub_output('{"result":[{}]}')

    def test_generate_id_and_secret(self):
        """client_id and client_secret are generated correctly"""
        task = CreateConnectedApp(self.project_config, self.task_config)
        task._generate_id_and_secret()
        assert len(task.client_id) == task.client_id_length
        assert len(task.client_secret) == task.client_secret_length
        assert re.match(r"^\w+$", task.client_id) is not None
        assert re.match(r"^\w+$", task.client_secret) is not None

    def test_build_package(self):
        """tempdir is populated with connected app and package.xml"""
        task = CreateConnectedApp(self.project_config, self.task_config)
        with temporary_dir() as tempdir:
            task.tempdir = tempdir
            connected_app_path = os.path.join(
                task.tempdir, "connectedApps", "{}.connectedApp".format(self.label)
            )
            task._build_package()
            assert os.path.isdir(os.path.join(task.tempdir, "connectedApps"))
            assert os.path.isfile(os.path.join(task.tempdir, "package.xml"))
            assert os.path.isfile(connected_app_path)
            with open(connected_app_path, "r") as f:
                connected_app = f.read()
                assert "<label>{}<".format(self.label) in connected_app
                assert "<contactEmail>{}<".format(self.email) in connected_app
                assert "<consumerKey>{}<".format(task.client_id) in connected_app
                assert "<consumerSecret>{}<".format(task.client_secret) in connected_app

    def test_connect_service(self):
        """connected app gets added to the keychain connected_app service"""
        self.project_config.config["services"] = {
            "connected_app": {
                "attributes": {"callback_url": {}, "client_id": {}, "client_secret": {}}
            }
        }
        task = CreateConnectedApp(self.project_config, self.task_config)
        task._connect_service()
        connected_app = self.project_config.keychain.get_service(
            "connected_app", self.label
        )
        assert connected_app.callback_url == "http://localhost:8080/callback"
        assert connected_app.client_id == task.client_id
        assert connected_app.client_secret == task.client_secret

    def test_validate_service_overwrite_false(self):
        """attempting to overwrite connected_app service without overwrite = True fails"""
        self.project_config.config["services"] = {
            "connected_app": {
                "attributes": {"callback_url": {}, "client_id": {}, "client_secret": {}}
            }
        }
        self.project_config.keychain.set_service(
            "connected_app",
            self.label,
            ServiceConfig(
                {
                    "callback_url": "http://callback",
                    "client_id": "ClientId",
                    "client_secret": "ClientSecret",
                }
            ),
        )
        task = CreateConnectedApp(self.project_config, self.task_config)
        with pytest.raises(
            TaskOptionsError, match="^The CumulusCI keychain already contains"
        ):
            task._validate_connect_service()

    @mock.patch("cumulusci.tasks.sfdx.SFDXBaseTask._run_task")
    def test_run_task(self, run_task_mock):
        """_run_task formats command, calls SFDXBaseTask._run_task, and does not connect service by default"""
        self.project_config.config["services"] = {
            "connected_app": {
                "attributes": {"callback_url": {}, "client_id": {}, "client_secret": {}}
            }
        }
        task = CreateConnectedApp(self.project_config, self.task_config)
        task._run_task()
        run_task_mock.assert_called_once()
        assert not os.path.isdir(task.tempdir)
        connected_app = self.project_config.keychain.get_service("connected_app")
        assert connected_app is DEFAULT_CONNECTED_APP

    @mock.patch("cumulusci.tasks.sfdx.SFDXBaseTask._run_task")
    @mock.patch("cumulusci.tasks.connectedapp.CreateConnectedApp._connect_service")
    def test_run_task_connect(self, run_task_mock, connect_service_mock):
        """_run_task calls _connect_service if connect option is True"""
        self.project_config.config["services"] = {
            "connected_app": {
                "attributes": {"callback_url": {}, "client_id": {}, "client_secret": {}}
            }
        }
        self.task_config.config["options"]["connect"] = True
        task = CreateConnectedApp(self.project_config, self.task_config)
        task._run_task()
        run_task_mock.assert_called_once()
        connect_service_mock.assert_called_once()
