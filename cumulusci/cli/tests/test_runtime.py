from datetime import date
from datetime import timedelta
from unittest import mock
import os
import sys
import unittest

import click

import cumulusci
from cumulusci.cli.runtime import CliRuntime
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import OrgNotFound


class TestCliRuntime(unittest.TestCase):
    key = "1234567890abcdef"

    def setup_method(self, method):
        os.chdir(os.path.dirname(cumulusci.__file__))
        self.environ_mock = mock.patch.dict(os.environ, {"CUMULUSCI_KEY": self.key})
        self.environ_mock.start()

    def teardown_method(self, method):
        self.environ_mock.stop()

    def test_init(self):
        config = CliRuntime()

        for key in {"cumulusci", "tasks", "flows", "services", "orgs", "project"}:
            self.assertIn(key, config.universal_config.config)
        self.assertEqual("CumulusCI", config.project_config.project__name)
        for key in {"services", "orgs", "app"}:
            self.assertIn(key, config.keychain.config)
        self.assertIn(config.project_config.repo_root, sys.path)

    @mock.patch("cumulusci.cli.runtime.CliRuntime._load_project_config")
    def test_load_project_config_error(self, load_proj_cfg_mock):
        load_proj_cfg_mock.side_effect = ConfigError

        with self.assertRaises(click.UsageError):
            CliRuntime()

    @mock.patch("cumulusci.cli.runtime.keyring")
    def test_get_keychain_key__migrates_from_env_to_keyring(self, keyring):
        keyring.get_password.return_value = None

        config = CliRuntime()
        self.assertEqual(self.key, config.keychain.key)
        keyring.set_password.assert_called_once_with(
            "cumulusci", "CUMULUSCI_KEY", self.key
        )

    @mock.patch("cumulusci.cli.runtime.keyring")
    def test_get_keychain_key__env_takes_precedence(self, keyring):
        if os.environ.get("CUMULUSCI_KEYCHAIN_CLASS"):
            del os.environ["CUMULUSCI_KEYCHAIN_CLASS"]
        keyring.get_password.return_value = "overridden"

        config = CliRuntime()
        self.assertEqual(self.key, config.keychain.key)

    @mock.patch("cumulusci.cli.runtime.keyring")
    def test_get_keychain_key__generates_key(self, keyring):
        del os.environ["CUMULUSCI_KEY"]
        if os.environ.get("CUMULUSCI_KEYCHAIN_CLASS"):
            del os.environ["CUMULUSCI_KEYCHAIN_CLASS"]
        keyring.get_password.return_value = None

        config = CliRuntime()
        self.assertNotEqual(self.key, config.keychain.key)
        self.assertEqual(16, len(config.keychain.key))

    @mock.patch("cumulusci.cli.runtime.keyring")
    def test_get_keychain_key__warns_if_generated_key_cannot_be_stored(self, keyring):
        del os.environ["CUMULUSCI_KEY"]
        keyring.get_password.side_effect = Exception

        with self.assertRaises(click.UsageError):
            CliRuntime()

    def test_get_org(self):
        config = CliRuntime()
        config.keychain = mock.Mock()
        config.keychain.get_org.return_value = org_config = OrgConfig({}, "test")

        org_name, org_config_result = config.get_org("test")
        self.assertEqual("test", org_name)
        self.assertIs(org_config, org_config_result)

    def test_get_org_default(self):
        config = CliRuntime()
        config.keychain = mock.Mock()
        org_config = OrgConfig({}, "test")
        config.keychain.get_default_org.return_value = ("test", org_config)

        org_name, org_config_result = config.get_org()
        self.assertEqual("test", org_name)
        self.assertIs(org_config, org_config_result)

    def test_get_org_missing(self):
        config = CliRuntime()
        config.keychain = mock.Mock()
        config.keychain.get_org.return_value = None

        with self.assertRaises(click.UsageError):
            org_name, org_config_result = config.get_org("test", fail_if_missing=True)

    def test_check_org_expired(self):
        config = CliRuntime()
        config.keychain = mock.Mock()
        org_config = OrgConfig(
            {
                "scratch": True,
                "date_created": date.today() - timedelta(days=2),
                "expired": True,
            },
            "test",
        )

        config.check_org_expired("test", org_config)
        config.keychain.create_scratch_org.assert_called_once()

    def test_check_org_overwrite_not_found(self):
        config = CliRuntime()
        config.keychain.get_org = mock.Mock(side_effect=OrgNotFound)

        self.assertTrue(config.check_org_overwrite("test"))

    def test_check_org_overwrite_scratch_exists(self):
        config = CliRuntime()
        config.keychain.get_org = mock.Mock(
            return_value=OrgConfig({"scratch": True, "created": True}, "test")
        )

        with self.assertRaises(click.ClickException):
            config.check_org_overwrite("test")

    def test_check_org_overwrite_non_scratch_exists(self):
        config = CliRuntime()
        config.keychain.get_org = mock.Mock(
            return_value=OrgConfig({"scratch": False}, "test")
        )

        with self.assertRaises(click.ClickException):
            config.check_org_overwrite("test")

    def test_check_cumulusci_version(self):
        config = CliRuntime()
        config.project_config.minimum_cumulusci_version = "999"

        with self.assertRaises(click.UsageError):
            config.check_cumulusci_version()

    @mock.patch("cumulusci.cli.runtime.call")
    @mock.patch("cumulusci.cli.runtime.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert_osx(self, echo_mock, shell_mock):
        config = CliRuntime()

        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
        self.assertIn("osascript", shell_mock.call_args[0][0])

    @mock.patch("cumulusci.cli.runtime.call")
    @mock.patch("cumulusci.cli.runtime.click.echo")
    @mock.patch("sys.platform", "linux2")
    def test_alert_linux(self, echo_mock, shell_mock):
        config = CliRuntime()

        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
        self.assertIn("notify-send", shell_mock.call_args[0][0])

    @mock.patch("cumulusci.cli.runtime.call")
    @mock.patch("cumulusci.cli.runtime.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert__disabled(self, echo_mock, shell_mock):
        config = CliRuntime()
        config.project_config.dev_config__no_alert = True

        config.alert("hello")
        echo_mock.assert_not_called()
        shell_mock.assert_not_called()

    @mock.patch("cumulusci.cli.runtime.call")
    @mock.patch("cumulusci.cli.runtime.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert__os_error(self, echo_mock, shell_mock):
        shell_mock.side_effect = OSError
        config = CliRuntime()
        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
