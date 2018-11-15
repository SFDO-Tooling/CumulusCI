from collections import OrderedDict
from datetime import date
import io
import json
import os
import shutil
import tempfile
import time
import unittest

import click
import mock
import pkg_resources
import requests
import responses

import cumulusci
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import TaskConfig, FlowConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.cli import cci
from cumulusci.cli.config import CliConfig
from cumulusci.tests.util import create_project_config
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
                {
                    "test": [
                        OrderedDict(
                            (
                                ("list", ["list"]),
                                ("dict", {"key": "value"}),
                                ("str", "str"),
                            )
                        )
                    ]
                }
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

    @mock.patch("click.echo")
    def test_version(self, echo):
        run_click_command(cci.version)
        echo.assert_called_once_with(cumulusci.__version__)

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

    @mock.patch("cumulusci.cli.cci.click")
    def test_project_init(self, click):
        with temporary_dir() as d:
            os.mkdir(".git")

            click.prompt.side_effect = (
                "testproj",  # project_name
                "testpkg",  # package_name
                "testns",  # package_namespace
                "43.0",  # api_version
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
                    "cumulusci.yml",
                    "orgs/",
                    "orgs/beta.json",
                    "orgs/dev.json",
                    "orgs/feature.json",
                    "orgs/release.json",
                    "sfdx-project.json",
                    "src/",
                    "tests/",
                    "tests/standard_objects/",
                    "tests/standard_objects/create_contact.robot",
                ],
                recursive_list_files(),
            )

    def test_project_init_no_git(self):
        with temporary_dir() as d:
            with self.assertRaises(click.ClickException):
                run_click_command(cci.project_init)

    def test_project_init_already_initted(self):
        with temporary_dir() as d:
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

    @mock.patch("click.echo")
    def test_service_list(self, echo):
        config = mock.Mock()
        config.project_config.services = {"test": {"description": "Test Service"}}
        config.keychain.list_services.return_value = ["test"]

        run_click_command(cci.service_list, config=config)

        table = echo.call_args[0][0]
        self.assertEqual(
            """service  description   is_configured
-------  ------------  -------------
test     Test Service  *""",
            str(table),
        )

    def test_service_connect_list(self):
        multi_cmd = cci.ConnectServiceCommand()
        config = mock.Mock()
        config.project_config.services = {"test": {}}
        ctx = mock.Mock()

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect(self):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        config = mock.Mock()
        config.project_config.services__test__attributes = {"attr": {"required": False}}

        with mock.patch("cumulusci.cli.cci.TEST_CONFIG", config):
            cmd = multi_cmd.get_command(ctx, "test")
            run_click_command(cmd, project=True)

        config.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    @mock.patch("click.echo")
    def test_service_info(self, echo):
        service_config = mock.Mock()
        service_config.config = {"description": "Test Service"}
        config = mock.Mock()
        config.keychain.get_service.return_value = service_config

        run_click_command(cci.service_info, config=config, service_name="test")

        echo.assert_called_with("\x1b[1mdescription:\x1b[0m Test Service")

    @mock.patch("click.echo")
    def test_service_info_not_configured(self, echo):
        config = mock.Mock()
        config.keychain.get_service.side_effect = ServiceNotConfigured

        run_click_command(cci.service_info, config=config, service_name="test")

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

    def test_org_default_unset(self):
        config = mock.Mock()

        run_click_command(cci.org_default, config=config, org_name="test", unset=True)

        config.keychain.unset_default_org.assert_called_once()

    @mock.patch("sarge.Command")
    def test_org_import(self, cmd):
        config = mock.Mock()
        result = b"""{
            "result": {
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

    def test_org_info(self):
        org_config = mock.Mock()
        org_config.config = {"test": "test"}
        org_config.expires = date.today()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_info, config=config, org_name="test", print_json=False
            )

        org_config.refresh_oauth_token.assert_called_once()
        self.assertTrue(
            "".join(out).startswith("\x1b[1mtest:\x1b[0m testOrg expires on ")
        )
        config.keychain.set_org.assert_called_once_with(org_config)

    def test_org_info_json(self):
        org_config = mock.Mock()
        org_config.config = {"test": "test"}
        org_config.expires = date.today()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)

        out = []
        with mock.patch("click.echo", out.append):
            run_click_command(
                cci.org_info, config=config, org_name="test", print_json=True
            )

        org_config.refresh_oauth_token.assert_called_once()
        self.assertEqual('{\n    "test": "test"\n}', "".join(out))
        config.keychain.set_org.assert_called_once_with(org_config)

    @mock.patch("click.echo")
    def test_org_list(self, echo):
        config = mock.Mock()
        config.project_config.keychain.list_orgs.return_value = ["test1", "test2"]
        config.project_config.keychain.get_org.side_effect = [
            OrgConfig(
                {
                    "default": True,
                    "scratch": True,
                    "days_alive": 1,
                    "days": 7,
                    "expired": False,
                    "config_name": "dev",
                    "username": "test1@example.com",
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
                },
                "test2",
            ),
        ]

        run_click_command(cci.org_list, config=config)

        table = echo.call_args[0][0]
        self.assertEqual(
            """org    default  scratch  days    expired  config_name  username
-----  -------  -------  ------  -------  -----------  -----------------
test1  *        *        1 of 7           dev          test1@example.com
test2                                     dev          test2@example.com""",
            str(table),
        )

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

    @mock.patch("click.echo")
    def test_task_list(self, echo):
        config = mock.Mock()
        config.project_config.list_tasks.return_value = [
            {"name": "test_task", "description": "Test Task", "group": "Test"}
        ]

        run_click_command(cci.task_list, config=config)

        table = echo.call_args_list[0][0][0]
        self.assertEqual(
            """task        description
----------  -----------

-- Test --
test_task   Test Task""",
            str(table),
        )

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

    def test_task_run(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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

    def test_task_run_not_found(self):
        config = mock.Mock()
        config.get_org.return_value = (None, None)
        config.project_config.tasks__test = None

        with self.assertRaises(TaskNotFoundError):
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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }

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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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
        config.project_config.tasks__test = {
            "class_path": "cumulusci.cli.tests.test_cci.DummyTask"
        }
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

    @mock.patch("click.echo")
    def test_flow_list(self, echo):
        config = mock.Mock()
        config.project_config.list_flows.return_value = [
            {"name": "test_flow", "description": "Test Flow"}
        ]

        run_click_command(cci.flow_list, config=config)

        table = echo.call_args_list[0][0][0]
        self.assertEqual(
            """flow       description
---------  -----------
test_flow  Test Flow""",
            str(table),
        )

    @mock.patch("click.echo")
    def test_flow_info(self, echo):
        config = mock.Mock()
        config.project_config.get_flow.return_value = FlowConfig(
            {"description": "Test Flow"}
        )

        run_click_command(cci.flow_info, config=config, flow_name="test")

        echo.assert_called_with("\x1b[1mdescription:\x1b[0m Test Flow")

    def test_flow_run(self):
        org_config = mock.Mock(scratch=True)
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)
        config.project_config.get_flow.return_value = FlowConfig(
            {"steps": {1: {"task": "test_task"}}}
        )
        config.project_config.get_task.return_value = TaskConfig(
            {
                "description": "Test Task",
                "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
            }
        )
        DummyTask._run_task = mock.Mock()

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

        DummyTask._run_task.assert_called_once()
        org_config.delete_org.assert_called_once()

    def test_flow_run_delete_non_scratch(self,):
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
                o=[("test_task__color", "blue")],
                skip=(),
                no_prompt=True,
            )

    def test_flow_run_usage_error(self):
        org_config = mock.Mock()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)
        config.project_config.get_flow.return_value = FlowConfig(
            {"steps": {1: {"task": "test_task"}}}
        )
        config.project_config.get_task.return_value = TaskConfig(
            {
                "description": "Test Task",
                "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
            }
        )
        DummyTask._run_task = mock.Mock(side_effect=TaskOptionsError)

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=[("test_task__color", "blue")],
                skip=(),
                no_prompt=True,
            )

    def test_flow_run_expected_failure(self):
        org_config = mock.Mock()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)
        config.project_config.get_flow.return_value = FlowConfig(
            {"steps": {1: {"task": "test_task"}}}
        )
        config.project_config.get_task.return_value = TaskConfig(
            {
                "description": "Test Task",
                "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
            }
        )
        DummyTask._run_task = mock.Mock(side_effect=ScratchOrgException)

        with self.assertRaises(click.ClickException):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=[("test_task__color", "blue")],
                skip=(),
                no_prompt=True,
            )

    @mock.patch("cumulusci.cli.cci.handle_sentry_event")
    def test_flow_run_unexpected_exception(self, handle_sentry_event):
        org_config = mock.Mock()
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)
        config.project_config.get_flow.return_value = FlowConfig(
            {"steps": {1: {"task": "test_task"}}}
        )
        config.project_config.get_task.return_value = TaskConfig(
            {
                "description": "Test Task",
                "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
            }
        )
        DummyTask._run_task = mock.Mock(side_effect=Exception)

        with self.assertRaises(Exception):
            run_click_command(
                cci.flow_run,
                config=config,
                flow_name="test",
                org="test",
                delete_org=False,
                debug=False,
                o=[("test_task__color", "blue")],
                skip=(),
                no_prompt=True,
            )

        handle_sentry_event.assert_called_once()

    @mock.patch("click.echo")
    def test_flow_run_org_delete_error(self, echo):
        org_config = mock.Mock(scratch=True)
        org_config.delete_org.side_effect = Exception
        config = mock.Mock()
        config.get_org.return_value = ("test", org_config)
        config.project_config.get_flow.return_value = FlowConfig(
            {"steps": {1: {"task": "test_task"}}}
        )
        config.project_config.get_task.return_value = TaskConfig(
            {
                "description": "Test Task",
                "class_path": "cumulusci.cli.tests.test_cci.DummyTask",
            }
        )
        DummyTask._run_task = mock.Mock()

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

        echo.assert_any_call(
            "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
        )


class SetTrace(Exception):
    pass


class DummyTask(BaseTask):
    task_options = {"color": {}}
