# -*- coding: utf-8 -*-
from datetime import date
from datetime import datetime
from datetime import timedelta
import io
import json
import os
import shutil
import tempfile
import time
import unittest

import click
from unittest import mock
import pkg_resources
import requests
import responses

import cumulusci
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.cli import cci
from cumulusci.cli.config import CliRuntime
from cumulusci.utils import temporary_dir


def run_click_command(cmd, *args, **kw):
    """Run a click command with a mock context and injected CCI config object.
    """
    config = kw.pop("config", None)
    with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
        with click.Context(command=mock.Mock()):
            return cmd.callback(*args, **kw)


def recursive_list_files(d="."):
    result = []
    for d, subdirs, files in os.walk(d):
        d = d.replace(os.path.sep, "/")
        if d != ".":
            result.append("/".join([d, ""])[2:])
        for f in files:
            result.append("/".join([d, f])[2:])
    result.sort()
    return result


class TestCCI(unittest.TestCase):
    @classmethod
    def setUpClass(self):
        self.tempdir = tempfile.mkdtemp()
        os.environ["HOME"] = self.tempdir
        os.environ["CUMULUSCI_KEY"] = ""

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.tempdir)

    def test_get_installed_version(self):
        result = cci.get_installed_version()
        self.assertEqual(cumulusci.__version__, str(result))

    @responses.activate
    def test_get_latest_final_version(self):
        responses.add(
            method="GET",
            url="https://pypi.org/pypi/cumulusci/json",
            body=json.dumps(
                {
                    "releases": {
                        "1.0b1": {},
                        "1.0": {},
                        "1.0.1.dev0": {},
                        "1.0.1": {},
                        "1.0.post1": {},
                    }
                }
            ),
            status=200,
        )
        result = cci.get_latest_final_version()
        self.assertEqual("1.0.1", result.base_version)

    @mock.patch("cumulusci.cli.cci.get_installed_version")
    @mock.patch("cumulusci.cli.cci.get_latest_final_version")
    @mock.patch("cumulusci.cli.cci.click")
    def test_check_latest_version(
        self, click, get_latest_final_version, get_installed_version
    ):
        with cci.timestamp_file() as f:
            f.write(str(time.time() - 4000))
        get_latest_final_version.return_value = pkg_resources.parse_version("2")
        get_installed_version.return_value = pkg_resources.parse_version("1")

        cci.check_latest_version()

        self.assertEqual(2, click.echo.call_count)

    @mock.patch("cumulusci.cli.cci.get_latest_final_version")
    @mock.patch("cumulusci.cli.cci.click")
    def test_check_latest_version_request_error(self, click, get_latest_final_version):
        with cci.timestamp_file() as f:
            f.write(str(time.time() - 4000))
        get_latest_final_version.side_effect = requests.exceptions.RequestException()

        cci.check_latest_version()

        click.echo.assert_any_call("Error checking cci version:")

    @mock.patch("pdb.post_mortem")
    def test_handle_exception_debug(self, post_mortem):
        cci.handle_exception_debug(config=None, debug=True)
        post_mortem.assert_called()

    def test_handle_exception_debug_throw(self):
        throw = Exception()
        try:
            cci.handle_exception_debug(config=None, debug=False, throw_exception=throw)
        except Exception as err:
            self.assertIs(throw, err)
        else:
            self.fail("Expected exception to be thrown.")

    @mock.patch("cumulusci.cli.cci.handle_sentry_event")
    def test_handle_exception_debug_sentry(self, handle_sentry_event):
        _marker = object()
        with self.assertRaises(Exception):
            cci.handle_exception_debug(config=_marker, debug=False)
        handle_sentry_event.assert_called_once_with(_marker, None)

    def test_render_recursive(self):
        out = []
        with mock.patch("click.echo", out.append):
            cci.render_recursive(
                {"test": [{"list": ["list"], "dict": {"key": "value"}, "str": "str"}]}
            )
        self.assertEqual(
            """\x1b[1mtest:\x1b[0m
    -
        \x1b[1mlist:\x1b[0m
            - list
        \x1b[1mdict:\x1b[0m
            \x1b[1mkey:\x1b[0m value
        \x1b[1mstr:\x1b[0m str""",
            "\n".join(out),
        )

    @mock.patch("cumulusci.cli.cci.webbrowser")
    @mock.patch("cumulusci.cli.cci.click")
    def test_handle_sentry_event(self, click, webbrowser):
        config = mock.Mock()
        click.confirm.return_value = True

        cci.handle_sentry_event(config, False)

        webbrowser.open.assert_called_once()

    def test_handle_sentry_event_no_event(self):
        config = mock.Mock()
        config.project_config.sentry_event = None

        cci.handle_sentry_event(config, True)

    def test_load_config__no_project(self):
        with temporary_dir():
            with self.assertRaises(SystemExit):
                cci.load_config()

    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    def test_main(self, check_latest_version, init_logger):
        run_click_command(cci.main)

        check_latest_version.assert_called_once()
        init_logger.assert_called_once()

    @mock.patch(
        "cumulusci.cli.cci.get_latest_final_version",
        mock.Mock(return_value=pkg_resources.parse_version("100")),
    )
    @mock.patch("click.echo")
    def test_version(self, echo):
        run_click_command(cci.version)
        assert cumulusci.__version__ in echo.call_args_list[1][0][0]

    @mock.patch("code.interact")
    def test_shell(self, interact):
        run_click_command(cci.shell)
        interact.assert_called_once()
        self.assertIn("config", interact.call_args[1]["local"])

    @mock.patch("code.interact")
    def test_shell__no_project(self, interact):
        with temporary_dir():
            run_click_command(cci.shell)
            interact.assert_called_once()

    def test_cover_command_groups(self):
        run_click_command(cci.project)
        run_click_command(cci.org)
        run_click_command(cci.task)
        run_click_command(cci.flow)
        run_click_command(cci.service)
        run_click_command(cci.service_connect)
        # no assertion; this test is for coverage of empty methods

    def test_validate_project_name(self):
        with self.assertRaises(click.UsageError):
            cci.validate_project_name("with spaces")

    @mock.patch("cumulusci.cli.cci.click")
    def test_project_init(self, click):
        with temporary_dir():
            os.mkdir(".git")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/Cumulus",  # github_url
                "default",  # git_default_branch
                "work/",  # git_prefix_feature
                "uat/",  # git_prefix_beta
                "rel/",  # git_prefix_release
                "%_TEST%",  # test_name_match
            )
            click.confirm.side_effect = (True, True)  # is managed?  # extending?

            run_click_command(cci.project_init)

            # Make sure expected files/dirs were created
            self.assertEqual(
                [
                    ".git/",
                    ".github/",
                    ".github/PULL_REQUEST_TEMPLATE.md",
                    ".gitignore",
                    "README.md",
                    "cumulusci.yml",
                    "datasets/",
                    "datasets/mapping.yml",
                    "orgs/",
                    "orgs/beta.json",
                    "orgs/dev.json",
                    "orgs/feature.json",
                    "orgs/release.json",
                    "robot/",
                    "robot/testproj/",
                    "robot/testproj/doc/",
                    "robot/testproj/resources/",
                    "robot/testproj/tests/",
                    "robot/testproj/tests/create_contact.robot",
                    "sfdx-project.json",
                    "src/",
                ],
                recursive_list_files(),
            )

    @mock.patch("cumulusci.cli.cci.click")
    def test_project_init_tasks(self, click):
        """Verify that the generated cumulusci.yml file is readable and has the proper robot task"""
        with temporary_dir():
            os.mkdir(".git")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
                "mdapi",  # source_format
                "3",  # extend other URL
                "https://github.com/SalesforceFoundation/Cumulus",  # github_url
                "default",  # git_default_branch
                "work/",  # git_prefix_feature
                "uat/",  # git_prefix_beta
                "rel/",  # git_prefix_release
                "%_TEST%",  # test_name_match
            )
            click.confirm.side_effect = (True, True)  # is managed?  # extending?

            run_click_command(cci.project_init)

            # verify we can load the generated yml
            cli_runtime = CliRuntime(load_keychain=False)

            # ...and verify it has the expected tasks
            config = cli_runtime.project_config.config_project
            expected_tasks = {
                "robot": {
                    "options": {
                        "suites": u"robot/testproj/tests",
                        "options": {"outputdir": "robot/testproj/results"},
                    }
                },
                "robot_testdoc": {
                    "options": {
                        "path": "robot/testproj/tests",
                        "output": "robot/testproj/doc/testproj_tests.html",
                    }
                },
            }
            self.assertDictEqual(config["tasks"], expected_tasks)

    def test_project_init_no_git(self):
        with temporary_dir():
            with self.assertRaises(click.ClickException):
                run_click_command(cci.project_init)

    def test_project_init_already_initted(self):
        with temporary_dir():
            os.mkdir(".git")
            with open("cumulusci.yml", "w"):
                pass  # create empty file

            with self.assertRaises(click.ClickException):
                run_click_command(cci.project_init)

    @mock.patch("click.echo")
    def test_project_info(self, echo):
        config = mock.Mock()
        config.project_config.project = {"test": "test"}

        run_click_command(cci.project_info, config=config)

        echo.assert_called_once_with("\x1b[1mtest:\x1b[0m test")

    def test_project_dependencies(self):
        out = []
        config = mock.Mock()
        config.project_config.pretty_dependencies.return_value = ["test:"]

        with mock.patch("click.echo", out.append):
            run_click_command(cci.project_dependencies, config=config)

        self.assertEqual("test:", "".join(out))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_list(self, cli_tbl):
        config = mock.Mock()
        config.is_global_keychain = False
        config.project_config.services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
        }
        config.keychain.list_services.return_value = ["test"]
        config.global_config.cli__plain_output = None

        run_click_command(
            cci.service_list, config=config, plain=False, print_json=False
        )

        cli_tbl.assert_called_with(
            [
                ["Name", "Description", "Configured"],
                ["bad", "Unconfigured Service", False],
                ["test", "Test Service", True],
            ],
            bool_cols=["Configured"],
            dim_rows=[1],
            title="Services",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_service_list_json(self, json_):
        services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
        }
        config = mock.Mock()
        config.is_global_keychain = False
        config.project_config.services = services
        config.keychain.list_services.return_value = ["test"]
        config.global_config.cli__plain_output = None

        run_click_command(cci.service_list, config=config, plain=False, print_json=True)

        json_.assert_called_with(services)

    def test_service_connect_list(self):
        multi_cmd = cci.ConnectServiceCommand()
        config = mock.Mock()
        config.is_global_keychain = False
        config.project_config.services = {"test": {}}
        ctx = mock.Mock()

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect_list_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        config = mock.Mock()
        config.is_global_keychain = True
        config.global_config.services = {"test": {}}
        ctx = mock.Mock()

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        config = mock.MagicMock()
        config.is_global_keychain = False
        config.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            cmd = multi_cmd.get_command(ctx, "test")
            run_click_command(cmd, project=True)

        config.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    def test_service_connect_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        config = mock.MagicMock()
        config.is_global_keychain = True
        config.global_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            cmd = multi_cmd.get_command(ctx, "test")
            run_click_command(cmd, project=True)

        config.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    def test_service_connect_invalid_service(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        config = mock.MagicMock()
        config.is_global_keychain = False
        config.project_config.services = {}

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            with self.assertRaises(click.UsageError):
                multi_cmd.get_command(ctx, "test")

    def test_service_connect_validator(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        config = mock.MagicMock()
        config.is_global_keychain = False
        config.project_config.services = {
            "test": {
                "attributes": {},
                "validator": "cumulusci.cli.tests.test_cci.validate_service",
            }
        }

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            cmd = multi_cmd.get_command(ctx, "test")
            try:
                run_click_command(cmd, project=True)
            except click.UsageError as e:
                self.assertEqual("Validation failed", str(e))
            else:
                self.fail("Did not raise expected click.UsageError")

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_info(self, cli_tbl):
        cli_tbl.table = mock.Mock()
        service_config = mock.Mock()
        service_config.config = {"description": "Test Service"}
        config = mock.Mock()
        config.keychain.get_service.return_value = service_config
        config.global_config.cli__plain_output = None

        run_click_command(
            cci.service_info, config=config, service_name="test", plain=False
        )

        cli_tbl.assert_called_with(
            [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
            title="test",
            wrap_cols=["Value"],
        )

    @mock.patch("click.echo")
    def test_service_info_not_configured(self, echo):
        config = mock.Mock()
        config.keychain.get_service.side_effect = ServiceNotConfigured

        run_click_command(
            cci.service_info, config=config, service_name="test", plain=False
        )

        self.assertIn("not configured for this project", echo.call_args[0][0])

    @mock.patch("webbrowser.open")
    def test_org_browser(self, browser_open):
        org_config = mock.Mock()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        run_click_command(cci.org_browser, config=config, org_name="test")

        org_config.refresh_oauth_token.assert_called_once()
        browser_open.assert_called_once()
        config.keychain.set_org.assert_called_once_with(org_config)

    def test_org_browser_not_found(self):
        config = mock.Mock()
        config.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(cci.org_browser, config=config, org_name="test")

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    @mock.patch("cumulusci.cli.cci.CaptureSalesforceOAuth")
    @responses.activate
    def test_org_connect(self, oauth):
        oauth.return_value = mock.Mock(
            return_value={"instance_url": "https://instance", "access_token": "BOGUS"}
        )
        config = mock.Mock()
        responses.add(
            method="GET",
            url="https://instance/services/oauth2/userinfo",
            body=b"{}",
            status=200,
        )

        run_click_command(
            cci.org_connect,
            config=config,
            org_name="test",
            sandbox=True,
            login_url="https://login.salesforce.com",
            default=True,
            global_org=False,
        )

        config.check_org_overwrite.assert_called_once()
        config.keychain.set_org.assert_called_once()
        config.keychain.set_default_org.assert_called_once_with("test")

    def test_org_connect_connected_app_not_configured(self):
        config = mock.Mock()
        config.keychain.get_service.side_effect = ServiceNotConfigured

        with self.assertRaises(ServiceNotConfigured):
            run_click_command(
                cci.org_connect,
                config=config,
                org_name="test",
                sandbox=True,
                login_url="https://login.salesforce.com",
                default=True,
                global_org=False,
            )

    def test_org_default(self):
        config = mock.Mock()

        run_click_command(cci.org_default, config=config, org_name="test", unset=False)

        config.keychain.set_default_org.assert_called_once_with("test")

    def test_org_default_not_found(self):
        config = mock.Mock()
        config.keychain.set_default_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.org_default, config=config, org_name="test", unset=False
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    def test_org_default_unset(self):
        config = mock.Mock()

        run_click_command(cci.org_default, config=config, org_name="test", unset=True)

        config.keychain.unset_default_org.assert_called_once()

    @mock.patch("sarge.Command")
    def test_org_import(self, cmd):
        config = mock.Mock()
        result = b"""{
            "result": {
                "createdDate": "1970-01-01T00:00:00.000Z",
                "expirationDate": "1970-01-01",
                "instanceUrl": "url",
                "accessToken": "access!token",
                "username": "test@test.org",
                "password": "password"
            }
        }"""
        cmd.return_value = mock.Mock(
            stderr=io.BytesIO(b""), stdout=io.BytesIO(result), returncode=0
        )

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_import,
                username_or_alias="test@test.org",
                org_name="test",
                config=config,
            )
            config.keychain.set_org.assert_called_once()
        self.assertTrue(
            "Imported scratch org: access, username: test@test.org" in "".join(out)
        )

    def test_calculate_org_days(self):
        info_1 = {
            "created_date": "1970-01-01T12:34:56.789Z",
            "expiration_date": "1970-01-02",
        }
        actual_days = cci.calculate_org_days(info_1)
        assert 1 == actual_days

        info_7 = {
            "created_date": "1970-01-01T12:34:56.789+0000",
            "expiration_date": "1970-01-08",
        }
        actual_days = cci.calculate_org_days(info_7)
        assert 7 == actual_days

        info_14 = {
            "created_date": "1970-01-01T12:34:56.000+0000",
            "expiration_date": "1970-01-15",
        }
        actual_days = cci.calculate_org_days(info_14)
        assert 14 == actual_days

    def test_org_info(self):
        org_config = mock.Mock()
        org_config.config = {"days": 1, "default": True, "password": None}
        org_config.expires = date.today()
        org_config.latest_api_version = "42.0"
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        with mock.patch("cumulusci.cli.cci.CliTable") as cli_tbl:
            run_click_command(
                cci.org_info, config=config, org_name="test", print_json=False
            )
            cli_tbl.assert_called_with(
                [
                    ["Key", "Value"],
                    ["\x1b[1mapi_version\x1b[0m", "42.0"],
                    ["\x1b[1mdays\x1b[0m", "1"],
                    ["\x1b[1mdefault\x1b[0m", "True"],
                    ["\x1b[1mpassword\x1b[0m", "None"],
                ],
                wrap_cols=["Value"],
            )

        config.keychain.set_org.assert_called_once_with(org_config)

    def test_org_info_json(self):
        class Unserializable(object):
            def __str__(self):
                return "<unserializable>"

        org_config = mock.Mock()
        org_config.config = {"test": "test", "unserializable": Unserializable()}
        org_config.expires = date.today()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_info, config=config, org_name="test", print_json=True
            )

        org_config.refresh_oauth_token.assert_called_once()
        self.assertEqual(
            '{\n    "test": "test",\n    "unserializable": "<unserializable>"\n}',
            "".join(out),
        )
        config.keychain.set_org.assert_called_once_with(org_config)

    def test_org_info_not_found(self):
        config = mock.Mock()
        config.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.org_info, config=config, org_name="test", print_json=False
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_org_list(self, cli_tbl):
        config = mock.Mock()
        config.global_config.cli__plain_output = None
        config.project_config.keychain.list_orgs.return_value = [
            "test0",
            "test1",
            "test2",
        ]
        config.project_config.keychain.get_org.side_effect = [
            ScratchOrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "date_created": datetime.now() - timedelta(days=8),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test0@example.com",
                },
                "test0",
            ),
            ScratchOrgConfig(
                {
                    "default": False,
                    "scratch": True,
                    "date_created": datetime.now(),
                    "days": 7,
                    "config_name": "dev",
                    "username": "test1@example.com",
                    "instance_url": "https://sneaky-master-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test1",
            ),
            OrgConfig(
                {
                    "default": False,
                    "scratch": False,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test2@example.com",
                    "instance_url": "https://dude-chillin-2330-dev-ed.cs22.my.salesforce.com",
                },
                "test2",
            ),
        ]

        run_click_command(cci.org_list, config=config, plain=False)

        scratch_table_call = mock.call(
            [
                ["Name", "Default", "Days", "Expired", "Config", "Domain"],
                ["test0", True, "7", True, "dev", ""],
                ["test1", False, "1/7", False, "dev", "sneaky-master-2330-dev-ed.cs22"],
            ],
            bool_cols=["Default"],
            title="Scratch Orgs",
            dim_rows=[0, 1],
        )
        persistent_table_call = mock.call(
            [["Name", "Default", "Username"], ["test2", False, "test2@example.com"]],
            bool_cols=["Default"],
            title="Persistent Orgs",
            wrap_cols=["Username"],
        )

        self.assertIn(scratch_table_call, cli_tbl.call_args_list)
        self.assertIn(persistent_table_call, cli_tbl.call_args_list)

    def test_org_remove(self):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        config = mock.Mock()
        config.keychain.get_org.return_value = org_config

        run_click_command(
            cci.org_remove, config=config, org_name="test", global_org=False
        )

        org_config.delete_org.assert_called_once()
        config.keychain.remove_org.assert_called_once_with("test", False)

    @mock.patch("click.echo")
    def test_org_remove_delete_error(self, echo):
        org_config = mock.Mock()
        org_config.can_delete.return_value = True
        org_config.delete_org.side_effect = Exception
        config = mock.Mock()
        config.keychain.get_org.return_value = org_config

        run_click_command(
            cci.org_remove, config=config, org_name="test", global_org=False
        )

        echo.assert_any_call("Deleting scratch org failed with error:")

    def test_org_remove_not_found(self):
        config = mock.Mock()
        config.keychain.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.org_remove, config=config, org_name="test", global_org=False
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    def test_org_scratch(self):
        config = mock.Mock()
        config.project_config.orgs__scratch = {"dev": {"orgName": "Dev"}}

        run_click_command(
            cci.org_scratch,
            config=config,
            config_name="dev",
            org_name="test",
            default=True,
            devhub="hub",
            days=7,
            no_password=True,
        )

        config.check_org_overwrite.assert_called_once()
        config.keychain.create_scratch_org.assert_called_with(
            "test", "dev", 7, set_password=False
        )
        config.keychain.set_default_org.assert_called_with("test")

    def test_org_scratch_no_configs(self):
        config = mock.Mock()
        config.project_config.orgs__scratch = None

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.org_scratch,
                config=config,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_config_not_found(self):
        config = mock.Mock()
        config.project_config.orgs__scratch = {"bogus": {}}

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.org_scratch,
                config=config,
                config_name="dev",
                org_name="test",
                default=True,
                devhub="hub",
                days=7,
                no_password=True,
            )

    def test_org_scratch_delete(self):
        org_config = mock.Mock()
        config = mock.Mock()
        config.keychain.get_org.return_value = org_config

        run_click_command(cci.org_scratch_delete, config=config, org_name="test")

        org_config.delete_org.assert_called_once()
        config.keychain.set_org.assert_called_once_with(org_config)

    def test_org_scratch_delete_not_scratch(self):
        org_config = mock.Mock(scratch=False)
        config = mock.Mock()
        config.keychain.get_org.return_value = org_config

        with self.assertRaises(click.UsageError):
            run_click_command(cci.org_scratch_delete, config=config, org_name="test")

    def test_org_scratch_delete_error(self):
        org_config = mock.Mock()
        org_config.delete_org.side_effect = ScratchOrgException
        config = mock.Mock()
        config.keychain.get_org.return_value = org_config

        with self.assertRaises(click.UsageError):
            run_click_command(cci.org_scratch_delete, config=config, org_name="test")

    def test_org_scratch_delete_not_found(self):
        config = mock.Mock()
        config.keychain.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(cci.org_scratch_delete, config=config, org_name="test")

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    @mock.patch("cumulusci.cli.cci.get_simple_salesforce_connection")
    @mock.patch("code.interact")
    def test_org_shell(self, mock_code, mock_sf):
        org_config = mock.Mock()
        org_config.instance_url = "https://salesforce.com"
        org_config.access_token = "TEST"
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        run_click_command(cci.org_shell, config=config, org_name="test")

        org_config.refresh_oauth_token.assert_called_once()
        mock_sf.assert_called_once_with(config.project_config, org_config)
        config.keychain.set_org.assert_called_once_with(org_config)

        mock_code.assert_called_once()
        self.assertIn("sf", mock_code.call_args[1]["local"])

    def test_org_shell_not_found(self):
        config = mock.Mock()
        config.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(cci.org_shell, config=config, org_name="test")

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_task_list(self, cli_tbl):
        config = mock.Mock()
        config.global_config.cli__plain_output = None
        config.project_config.list_tasks.return_value = [
            {"name": "test_task", "description": "Test Task", "group": "Test Group"}
        ]

        run_click_command(cci.task_list, config=config, plain=False, print_json=False)

        cli_tbl.assert_called_with(
            [["Task", "Description"], ["test_task", "Test Task"]],
            "Test Group",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_task_list_json(self, json_):
        task_dicts = {
            "name": "test_task",
            "description": "Test Task",
            "group": "Test Group",
        }
        config = mock.Mock()
        config.global_config.cli__plain_output = None
        config.project_config.list_tasks.return_value = [task_dicts]

        run_click_command(cci.task_list, config=config, plain=False, print_json=True)

        json_.assert_called_with([task_dicts])

    @mock.patch("cumulusci.cli.cci.doc_task")
    def test_task_doc(self, doc_task):
        config = mock.Mock()
        config.global_config.tasks = {"test": {}}

        run_click_command(cci.task_doc, config=config)
        doc_task.assert_called()

    @mock.patch("cumulusci.cli.cci.rst2ansi")
    @mock.patch("cumulusci.cli.cci.doc_task")
    def test_task_info(self, doc_task, rst2ansi):
        config = mock.Mock()
        config.project_config.tasks__test = {"options": {}}

        run_click_command(cci.task_info, config=config, task_name="test")

        doc_task.assert_called_once()
        rst2ansi.assert_called_once()

    def test_task_info__not_found(self):
        config = mock.Mock()
        config.project_config.get_task.side_effect = TaskNotFoundError
        with self.assertRaises(click.UsageError):
            run_click_command(cci.task_info, config=config, task_name="test")

    def test_task_run(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        DummyTask._run_task = mock.Mock()

        run_click_command(
            cci.task_run,
            config=config,
            task_name="test",
            org=None,
            o=[("color", "blue")],
            debug=False,
            debug_before=False,
            debug_after=False,
            no_prompt=True,
        )

        DummyTask._run_task.assert_called_once()

    def test_task_run_org_not_found(self):
        config = mock.Mock()
        config.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org="test",
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    def test_task_run_not_found(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(BaseGlobalConfig(), config={})

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

    def test_task_run_invalid_option(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config.get_task.return_value = TaskConfig(
            {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
        )

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("bogus", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

    @mock.patch("pdb.set_trace")
    def test_task_run_debug_before(self, set_trace):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        set_trace.side_effect = SetTrace

        with self.assertRaises(SetTrace):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=True,
                debug_after=False,
                no_prompt=True,
            )

    @mock.patch("pdb.set_trace")
    def test_task_run_debug_after(self, set_trace):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        set_trace.side_effect = SetTrace

        with self.assertRaises(SetTrace):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=True,
                no_prompt=True,
            )

    def test_task_run_usage_error(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        DummyTask._run_task.side_effect = TaskOptionsError

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

    def test_task_run_expected_failure(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config = BaseProjectConfig(
            None,
            config={
                "tasks": {
                    "test": {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
                }
            },
        )
        DummyTask._run_task.side_effect = ScratchOrgException

        with self.assertRaises(click.ClickException):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

    @mock.patch("cumulusci.cli.cci.handle_sentry_event")
    def test_task_run_unexpected_exception(self, handle_sentry_event):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config.get_task.return_value = TaskConfig(
            {"class_path": "cumulusci.cli.tests.test_cci.DummyTask"}
        )
        DummyTask._run_task.side_effect = Exception

        with self.assertRaises(Exception):
            run_click_command(
                cci.task_run,
                config=config,
                task_name="test",
                org=None,
                o=[("color", "blue")],
                debug=False,
                debug_before=False,
                debug_after=False,
                no_prompt=True,
            )

        handle_sentry_event.assert_called_once()

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_flow_list(self, cli_tbl):
        config = mock.Mock()
        config.project_config.list_flows.return_value = [
            {"name": "test_flow", "description": "Test Flow"}
        ]
        config.global_config.cli__plain_output = None
        run_click_command(cci.flow_list, config=config, plain=False, print_json=False)

        cli_tbl.assert_called_with(
            [["Name", "Description"], ["test_flow", "Test Flow"]],
            title="Flows",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_flow_list_json(self, json_):
        flows = [{"name": "test_flow", "description": "Test Flow"}]
        config = mock.Mock()
        config.project_config.list_flows.return_value = flows
        config.global_config.cli__plain_output = None

        run_click_command(cci.flow_list, config=config, plain=False, print_json=True)

        json_.assert_called_with(flows)

    @mock.patch("click.echo")
    def test_flow_info(self, echo):
        config = mock.Mock()
        flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
        config.get_flow.return_value = FlowCoordinator(None, flow_config)

        run_click_command(cci.flow_info, config=config, flow_name="test")

        echo.assert_called_with("Description: Test Flow")

    def test_flow_info__not_found(self):
        config = mock.Mock()
        config.get_flow.side_effect = FlowNotFoundError
        with self.assertRaises(click.UsageError):
            run_click_command(cci.flow_info, config=config, flow_name="test")

    def test_flow_run(self):
        org_config = mock.Mock(scratch=True, config={})
        config = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        config.get_org = mock.Mock(return_value=("test", org_config))
        config.get_flow = mock.Mock()

        run_click_command(
            cci.flow_run,
            config=config,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=[("test_task__color", "blue")],
            skip=(),
            no_prompt=True,
        )

        config.get_flow.assert_called_once_with(
            "test", options={"test_task": {"color": "blue"}}
        )
        org_config.delete_org.assert_called_once()

    def test_flow_run_org_not_found(self):
        config = mock.Mock()
        config.get_org.side_effect = OrgNotFound

        with self.assertRaises(click.ClickException) as cm:
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

        self.assertEqual("Org test does not exist in the keychain", str(cm.exception))

    def test_flow_run_delete_non_scratch(self):
        org_config = mock.Mock(scratch=False)
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=True,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

    def test_flow_run_usage_error(self):
        org_config = mock.Mock(config={})
        config = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        config.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock(side_effect=TaskOptionsError)

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

    def test_flow_run_expected_failure(self):
        org_config = mock.Mock(config={})
        config = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        config.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock(side_effect=ScratchOrgException("msg"))

        with self.assertRaises(click.ClickException) as e:
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )
            assert "msg" in str(e)

    @mock.patch("cumulusci.cli.cci.handle_sentry_event")
    def test_flow_run_unexpected_exception(self, handle_sentry_event):
        org_config = mock.Mock(config={})
        config = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        config.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock(side_effect=Exception)

        with self.assertRaises(Exception):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

        handle_sentry_event.assert_called_once()

    @mock.patch("click.echo")
    def test_flow_run_org_delete_error(self, echo):
        org_config = mock.Mock(scratch=True, config={})
        org_config.delete_org.side_effect = Exception
        config = CliRuntime(
            config={
                "flows": {"test": {"steps": {1: {"task": "test_task"}}}},
                "tasks": {
                    "test_task": {
                        "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
                        "description": "Test Task",
                    }
                },
            },
            load_keychain=False,
        )
        config.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock()

        run_click_command(
            cci.flow_run,
            config=config,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=None,
            skip=(),
            no_prompt=True,
        )

        echo.assert_any_call(
            "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
        )


class SetTrace(Exception):
    pass


class DummyTask(BaseTask):
    task_options = {"color": {}}


def validate_service(options):
    raise Exception("Validation failed")
