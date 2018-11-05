from datetime import date
from datetime import timedelta
import mock
import os
import sys
import unittest

import click

import cumulusci
from cumulusci.cli.config import CliConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound


class TestCliConfig(unittest.TestCase):
    key = "1234567890abcdef"

    @classmethod
    def setUpClass(cls):
        os.chdir(os.path.dirname(cumulusci.__file__))
        os.environ["CUMULUSCI_KEY"] = cls.key

    def test_init(self):
        config = CliConfig()

        for key in {"cumulusci", "tasks", "flows", "services", "orgs", "project"}:
            self.assertIn(key, config.global_config.config)
        self.assertEqual("CumulusCI", config.project_config.project__name)
        for key in {"services", "orgs", "app"}:
            self.assertIn(key, config.keychain.config)
        self.assertIn(config.project_config.repo_root, sys.path)

    @mock.patch("cumulusci.cli.config.CliConfig._load_project_config")
    def test_load_project_not_in_project(self, load_proj_cfg_mock):
        load_proj_cfg_mock.side_effect = NotInProject

        with self.assertRaises(click.UsageError):
            CliConfig()

    @mock.patch("cumulusci.cli.config.CliConfig._load_project_config")
    def test_load_project_config_no_file(self, load_proj_cfg_mock):
        load_proj_cfg_mock.side_effect = ProjectConfigNotFound
        with self.assertRaises(click.UsageError):
            CliConfig()

    @mock.patch("cumulusci.cli.config.CliConfig._load_project_config")
    def test_load_project_config_error(self, load_proj_cfg_mock):
        load_proj_cfg_mock.side_effect = ConfigError

        with self.assertRaises(click.UsageError):
            CliConfig()

    def test_load_keychain__no_key(self):
        with mock.patch.dict(os.environ, {"CUMULUSCI_KEY": ""}):
            with self.assertRaises(click.UsageError):
                config = CliConfig()

    def test_get_org(self):
        config = CliConfig()
        config.keychain = mock.Mock()
        config.keychain.get_org.return_value = org_config = OrgConfig({}, "test")

        org_name, org_config_result = config.get_org("test")
        self.assertEqual("test", org_name)
        self.assertIs(org_config, org_config_result)

    def test_get_org_default(self):
        config = CliConfig()
        config.keychain = mock.Mock()
        org_config = OrgConfig({}, "test")
        config.keychain.get_default_org.return_value = ("test", org_config)

        org_name, org_config_result = config.get_org()
        self.assertEqual("test", org_name)
        self.assertIs(org_config, org_config_result)

    def test_get_org_missing(self):
        config = CliConfig()
        config.keychain = mock.Mock()
        config.keychain.get_org.return_value = None

        with self.assertRaises(click.UsageError):
            org_name, org_config_result = config.get_org("test", fail_if_missing=True)

    @mock.patch("click.confirm")
    def test_check_org_expired(self, confirm):
        config = CliConfig()
        config.keychain = mock.Mock()
        org_config = OrgConfig(
            {
                "scratch": True,
                "date_created": date.today() - timedelta(days=2),
                "expired": True,
            },
            "test",
        )
        confirm.return_value = True

        config.check_org_expired("test", org_config)
        config.keychain.create_scratch_org.assert_called_once()

    @mock.patch("click.confirm")
    def test_check_org_expired_decline(self, confirm):
        config = CliConfig()
        config.keychain = mock.Mock()
        org_config = OrgConfig(
            {
                "scratch": True,
                "date_created": date.today() - timedelta(days=2),
                "expired": True,
            },
            "test",
        )
        confirm.return_value = False

        with self.assertRaises(click.ClickException):
            config.check_org_expired("test", org_config)

    def test_check_org_overwrite_not_found(self):
        config = CliConfig()
        config.keychain.get_org = mock.Mock(side_effect=OrgNotFound)

        self.assertTrue(config.check_org_overwrite("test"))

    def test_check_org_overwrite_scratch_exists(self):
        config = CliConfig()
        config.keychain.get_org = mock.Mock(
            return_value=OrgConfig({"scratch": True, "created": True}, "test")
        )

        with self.assertRaises(click.ClickException):
            config.check_org_overwrite("test")

    def test_check_org_overwrite_non_scratch_exists(self):
        config = CliConfig()
        config.keychain.get_org = mock.Mock(
            return_value=OrgConfig({"scratch": False}, "test")
        )

        with self.assertRaises(click.ClickException):
            config.check_org_overwrite("test")

    def test_check_cumulusci_version(self):
        config = CliConfig()
        config.project_config.minimum_cumulusci_version = "999"

        with self.assertRaises(click.UsageError):
            config.check_cumulusci_version()

    @mock.patch("cumulusci.cli.config.call")
    @mock.patch("cumulusci.cli.config.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert_osx(self, echo_mock, shell_mock):
        config = CliConfig()

        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
        self.assertIn("osascript", shell_mock.call_args[0][0])

    @mock.patch("cumulusci.cli.config.call")
    @mock.patch("cumulusci.cli.config.click.echo")
    @mock.patch("sys.platform", "linux2")
    def test_alert_linux(self, echo_mock, shell_mock):
        config = CliConfig()

        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
        self.assertIn("notify-send", shell_mock.call_args[0][0])

    @mock.patch("cumulusci.cli.config.call")
    @mock.patch("cumulusci.cli.config.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert__disabled(self, echo_mock, shell_mock):
        config = CliConfig()
        config.project_config.dev_config__no_alert = True

        config.alert("hello")
        echo_mock.assert_not_called()
        shell_mock.assert_not_called()

    @mock.patch("cumulusci.cli.config.call")
    @mock.patch("cumulusci.cli.config.click.echo")
    @mock.patch("sys.platform", "darwin")
    def test_alert__os_error(self, echo_mock, shell_mock):
        shell_mock.side_effect = OSError
        config = CliConfig()
        config.alert("hello")
        echo_mock.assert_called_once()
        shell_mock.assert_called_once()
