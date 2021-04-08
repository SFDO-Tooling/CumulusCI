# -*- coding: utf-8 -*-
import io
import json
import os
import shutil
import tempfile
import time
import pytest
import unittest
from pathlib import Path
import contextlib

import click
from unittest import mock
import pkg_resources
import requests
import responses
from requests.exceptions import ConnectionError

import cumulusci
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.cli import cci
from cumulusci.cli.runtime import CliRuntime
from cumulusci.utils import temporary_dir
from cumulusci.cli.tests.utils import run_click_command, DummyTask

MagicMock = mock.MagicMock()


class TestCCI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.global_tempdir = tempfile.gettempdir()
        cls.tempdir = tempfile.mkdtemp()
        cls.environ_mock = mock.patch.dict(
            os.environ, {"HOME": tempfile.mkdtemp(), "CUMULUSCI_KEY": ""}
        )
        cls.environ_mock.start()
        assert cls.global_tempdir in os.environ["HOME"]

    @classmethod
    def tearDownClass(cls):
        assert cls.global_tempdir in os.environ["HOME"]
        cls.environ_mock.stop()
        shutil.rmtree(cls.tempdir)

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

        click.echo.assert_called_once()

    @mock.patch("cumulusci.cli.cci.get_latest_final_version")
    @mock.patch("cumulusci.cli.cci.click")
    def test_check_latest_version_request_error(self, click, get_latest_final_version):
        with cci.timestamp_file() as f:
            f.write(str(time.time() - 4000))
        get_latest_final_version.side_effect = requests.exceptions.RequestException()

        cci.check_latest_version()

        click.echo.assert_any_call("Error checking cci version:", err=True)

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    def test_main(
        self,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"
        cci.main()

        check_latest_version.assert_called_once()
        init_logger.assert_called_once()
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        tee.assert_called_once()

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("pdb.post_mortem")
    @mock.patch("sys.exit")
    def test_main__debug(
        self,
        sys_exit,
        post_mortem,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        cli.side_effect = Exception
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")

        cci.main(["cci", "--debug"])

        check_latest_version.assert_called_once()
        init_logger.assert_called_once_with(log_requests=True)
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        post_mortem.assert_called_once()
        sys_exit.assert_called_once_with(1)
        get_tempfile_logger.assert_called_once()
        tee.assert_called_once()

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("pdb.post_mortem")
    def test_main__cci_show_stacktraces(
        self,
        post_mortem,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        runtime = mock.Mock()
        runtime.universal_config.cli__show_stacktraces = True
        CliRuntime.return_value = runtime
        cli.side_effect = Exception
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")

        with self.assertRaises(Exception):
            cci.main(["cci"])

        check_latest_version.assert_called_once()
        init_logger.assert_called_once_with(log_requests=False)
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        post_mortem.assert_not_called()

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("sys.exit")
    def test_main__abort(
        self, sys_exit, cli, init_logger, get_tempfile_logger, tee_stdout_stderr
    ):
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")
        cli.side_effect = click.Abort
        cci.main(["cci"])
        cli.assert_called_once()
        sys_exit.assert_called_once_with(1)

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.init_logger")
    @mock.patch("cumulusci.cli.cci.check_latest_version")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.cli.cci.cli")
    @mock.patch("pdb.post_mortem")
    @mock.patch("sys.exit")
    def test_main__error(
        self,
        sys_exit,
        post_mortem,
        cli,
        CliRuntime,
        check_latest_version,
        init_logger,
        get_tempfile_logger,
        tee,
    ):
        runtime = mock.Mock()
        runtime.universal_config.cli__show_stacktraces = False
        CliRuntime.return_value = runtime

        cli.side_effect = Exception
        get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"

        cci.main(["cci", "org", "info"])

        check_latest_version.assert_called_once()
        init_logger.assert_called_once_with(log_requests=False)
        CliRuntime.assert_called_once()
        cli.assert_called_once()
        post_mortem.call_count == 0
        sys_exit.assert_called_once_with(1)
        get_tempfile_logger.assert_called_once()
        tee.assert_called_once()

        os.remove("tempfile.log")

    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    def test_main__CliRuntime_error(self, CliRuntime, get_tempfile_logger, tee):
        CliRuntime.side_effect = CumulusCIException("something happened")
        get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            with mock.patch("sys.exit") as sys_exit:
                sys_exit.side_effect = SystemExit  # emulate real sys.exit
                with pytest.raises(SystemExit):
                    cci.main(["cci", "org", "info"])

        assert "something happened" in stderr.getvalue()

        tempfile = Path("tempfile.log")
        tempfile.unlink()

    @mock.patch("cumulusci.cli.cci.init_logger")  # side effects break other tests
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("sys.exit", MagicMock())
    def test_handle_org_name(
        self, CliRuntime, tee_stdout_stderr, get_tempfile_logger, init_logger
    ):

        # get_tempfile_logger doesn't clean up after itself which breaks other tests
        get_tempfile_logger.return_value = mock.Mock(), ""

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            cci.main(["cci", "org", "default", "xyzzy"])
        assert "xyzzy is now the default org" in stdout.getvalue(), stdout.getvalue()

        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            cci.main(["cci", "org", "default", "--org", "xyzzy2"])
        assert "xyzzy2 is now the default org" in stdout.getvalue(), stdout.getvalue()

        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            cci.main(["cci", "org", "default", "xyzzy1", "--org", "xyzzy2"])
        assert "not both" in stderr.getvalue(), stderr.getvalue()

        CliRuntime().keychain.get_default_org.return_value = ("xyzzy3", None)

        # cci org remove should really need an attached org
        with contextlib.redirect_stderr(io.StringIO()) as stderr:
            cci.main(["cci", "org", "remove"])
        assert (
            "Please specify ORGNAME or --org ORGNAME" in stderr.getvalue()
        ), stderr.getvalue()

    @mock.patch("cumulusci.cli.cci.init_logger")  # side effects break other tests
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
    @mock.patch("sys.exit")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    def test_cci_org_default__no_orgname(
        self, CliRuntime, exit, tee_stdout_stderr, get_tempfile_logger, init_logger
    ):
        # get_tempfile_logger doesn't clean up after itself which breaks other tests
        get_tempfile_logger.return_value = mock.Mock(), ""

        CliRuntime().keychain.get_default_org.return_value = ("xyzzy4", None)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            cci.main(["cci", "org", "default"])
        assert "xyzzy4 is the default org" in stdout.getvalue(), stdout.getvalue()

        CliRuntime().keychain.get_default_org.return_value = (None, None)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            cci.main(["cci", "org", "default"])
        assert "There is no default org" in stdout.getvalue(), stdout.getvalue()

    @mock.patch("cumulusci.cli.cci.init_logger", mock.Mock())
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr", mock.MagicMock())
    @mock.patch("cumulusci.tasks.salesforce.Deploy.__call__", mock.Mock())
    @mock.patch("sys.exit", mock.Mock())
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.tasks.salesforce.Deploy.__init__")
    def test_cci_run_task_options__with_dash(
        self,
        Deploy,
        CliRuntime,
        get_tempfile_logger,
    ):
        # get_tempfile_logger doesn't clean up after itself which breaks other tests
        Deploy.return_value = None
        get_tempfile_logger.return_value = mock.Mock(), ""
        CliRuntime.return_value = runtime = mock.Mock()
        runtime.get_org.return_value = ("test", mock.Mock())
        runtime.project_config = BaseProjectConfig(
            runtime.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {
                    "deploy": {"class_path": "cumulusci.tasks.salesforce.Deploy"}
                },
            },
        )

        cci.main(
            ["cci", "task", "run", "deploy", "--path", "x", "--clean-meta-xml", "False"]
        )
        task_config = Deploy.mock_calls[0][1][1]
        assert "clean_meta_xml" in task_config.options

    @mock.patch("cumulusci.cli.cci.init_logger", mock.Mock())
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr", mock.MagicMock())
    @mock.patch("cumulusci.tasks.salesforce.Deploy.__call__", mock.Mock())
    @mock.patch("sys.exit", mock.Mock())
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    @mock.patch("cumulusci.cli.cci.CliRuntime")
    @mock.patch("cumulusci.tasks.salesforce.Deploy.__init__")
    def test_cci_run_task_options__old_style_with_dash(
        self,
        Deploy,
        CliRuntime,
        get_tempfile_logger,
    ):
        # get_tempfile_logger doesn't clean up after itself which breaks other tests
        Deploy.return_value = None
        get_tempfile_logger.return_value = mock.Mock(), ""
        CliRuntime.return_value = runtime = mock.Mock()
        runtime.get_org.return_value = ("test", mock.Mock())
        runtime.project_config = BaseProjectConfig(
            runtime.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {
                    "deploy": {"class_path": "cumulusci.tasks.salesforce.Deploy"}
                },
            },
        )

        cci.main(
            [
                "cci",
                "task",
                "run",
                "deploy",
                "--path",
                "x",
                "-o",
                "clean-meta-xml",
                "False",
            ]
        )
        task_config = Deploy.mock_calls[0][1][1]
        assert "clean_meta_xml" in task_config.options

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_exception(self, style, traceback, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()

        error = "Something bad happened."
        cci_open.__enter__.return_value = mock.Mock()

        cci.handle_exception(error, False, logfile_path)

        style.call_args_list[0][0] == f"Error: {error}"
        style.call_args_list[1][0] == cci.SUGGEST_ERROR_COMMAND
        traceback.print_exc.assert_called_once()

        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_exception__error_cmd(self, style, traceback, cci_open):
        """Ensure we don't write to logfiles when running `cci error ...` commands."""
        error = "Something bad happened."
        logfile_path = None
        cci.handle_exception(error, False, logfile_path)

        style.call_args_list[0][0] == f"Error: {error}"
        style.call_args_list[1][0] == cci.SUGGEST_ERROR_COMMAND
        assert not cci_open.called

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.traceback")
    @mock.patch("cumulusci.cli.cci.click.style")
    def test_handle_click_exception(self, style, traceback, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()
        cci_open.__enter__.return_value = mock.Mock()

        cci.handle_exception(click.ClickException("oops"), False, logfile_path)
        style.call_args_list[0][0] == "Error: oops"

        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.open")
    @mock.patch("cumulusci.cli.cci.connection_error_message")
    def test_handle_connection_exception(self, connection_msg, cci_open):
        logfile_path = "file.log"
        Path(logfile_path).touch()

        cci.handle_exception(ConnectionError(), False, logfile_path)
        connection_msg.assert_called_once()
        os.remove(logfile_path)

    @mock.patch("cumulusci.cli.cci.click.style")
    def test_connection_exception_message(self, style):
        cci.connection_error_message()
        style.assert_called_once_with(
            (
                "We encountered an error with your internet connection. "
                "Please check your connection and try the last cci command again."
            ),
            fg="red",
        )

    def test_cli(self):
        run_click_command(cci.cli)

    @mock.patch(
        "cumulusci.cli.cci.get_latest_final_version",
        mock.Mock(return_value=pkg_resources.parse_version("100")),
    )
    @mock.patch("click.echo")
    def test_version(self, echo):
        run_click_command(cci.version)
        assert cumulusci.__version__ in echo.call_args_list[1][0][0]

    @mock.patch(
        "cumulusci.cli.cci.get_latest_final_version",
        mock.Mock(return_value=pkg_resources.parse_version("100")),
    )
    @mock.patch("click.echo")
    def test_version__latest(self, echo):
        with mock.patch(
            "cumulusci.cli.cci.get_latest_final_version", cci.get_installed_version
        ):
            run_click_command(cci.version)
        assert (
            "You have the latest version of CumulusCI." in echo.call_args_list[-2][0][0]
        )

    @mock.patch("code.interact")
    def test_shell(self, interact):
        run_click_command(cci.shell)
        interact.assert_called_once()
        self.assertIn("config", interact.call_args[1]["local"])
        self.assertIn("runtime", interact.call_args[1]["local"])

    @mock.patch("runpy.run_path")
    def test_shell_script(self, runpy):
        run_click_command(cci.shell, script="foo.py")
        runpy.assert_called_once()
        self.assertIn("config", runpy.call_args[1]["init_globals"])
        self.assertIn("runtime", runpy.call_args[1]["init_globals"])
        assert runpy.call_args[0][0] == "foo.py", runpy.call_args[0]

    @mock.patch("builtins.print")
    def test_shell_code(self, print):
        run_click_command(cci.shell, python="print(config, runtime)")
        print.assert_called_once()

    @mock.patch("cumulusci.cli.cci.print")
    def test_shell_mutually_exclusive_args(self, print):
        with self.assertRaises(Exception) as e:
            run_click_command(
                cci.shell, script="foo.py", python="print(config, runtime)"
            )
        self.assertIn("Cannot specify both", str(e.exception))

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

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.project_config.services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
        }
        runtime.keychain.list_services.return_value = ["test"]
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=False
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
        runtime = mock.Mock()
        runtime.project_config.services = services
        runtime.keychain.list_services.return_value = ["test"]
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=True
        )

        json_.assert_called_with(services)

    def test_service_connect_list(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config.services = {"test": {}}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect_list_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config = None
        runtime.universal_config.services = {"test": {}}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            result = multi_cmd.list_commands(ctx)
        self.assertEqual(["test"], result)

    def test_service_connect(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(ctx.obj, project=True)

        runtime.keychain.set_service.assert_called_once()

        run_click_command(cmd, project=False)

    def test_service_connect_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config = None
        runtime.universal_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(ctx.obj, project=True)

            runtime.keychain.set_service.assert_called_once()

            cmd.callback(ctx.obj, project=False)

    def test_service_connect_invalid_service(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config.services = {}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            with self.assertRaises(click.UsageError):
                multi_cmd.get_command(ctx, "test")

    def test_service_connect_validator(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {
                "attributes": {},
                "validator": "cumulusci.cli.tests.test_cci.validate_service",
            }
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            with pytest.raises(Exception, match="Validation failed"):
                cmd.callback(ctx.obj, project=True)

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_info(self, cli_tbl):
        cli_tbl._table = mock.Mock()
        service_config = mock.Mock()
        service_config.config = {"description": "Test Service"}
        runtime = mock.Mock()
        runtime.keychain.get_service.return_value = service_config
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_info, runtime=runtime, service_name="test", plain=False
        )

        cli_tbl.assert_called_with(
            [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
            title="test",
            wrap_cols=["Value"],
        )

    @mock.patch("click.echo")
    def test_service_info_not_configured(self, echo):
        runtime = mock.Mock()
        runtime.keychain.get_service.side_effect = ServiceNotConfigured

        run_click_command(
            cci.service_info, runtime=runtime, service_name="test", plain=False
        )

        self.assertIn("not configured for this project", echo.call_args[0][0])

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_task_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.universal_config.cli__plain_output = None
        runtime.get_available_tasks.return_value = [
            {"name": "test_task", "description": "Test Task", "group": "Test Group"}
        ]

        run_click_command(cci.task_list, runtime=runtime, plain=False, print_json=False)

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
        runtime = mock.Mock()
        runtime.universal_config.cli__plain_output = None
        runtime.get_available_tasks.return_value = [task_dicts]

        run_click_command(cci.task_list, runtime=runtime, plain=False, print_json=True)

        json_.assert_called_with([task_dicts])

    @mock.patch("cumulusci.cli.cci.doc_task", return_value="docs")
    def test_task_doc(self, doc_task):
        runtime = mock.Mock()
        runtime.universal_config.tasks = {"test": {}}
        run_click_command(cci.task_doc, runtime=runtime, project=False)
        doc_task.assert_called()

    def test_task_doc__project__outside_project(self):
        runtime = mock.Mock()
        runtime.project_config = None
        with pytest.raises(click.UsageError):
            run_click_command(cci.task_doc, runtime=runtime, project=True)

    @mock.patch("click.echo")
    @mock.patch("cumulusci.cli.cci.doc_task", return_value="docs")
    def test_task_doc_project(self, doc_task, echo):
        runtime = mock.Mock()
        runtime.universal_config = {"tasks": {}}
        runtime.project_config = BaseProjectConfig(
            runtime.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {"task1": {"a": "b"}, "task2": {}},
            },
        )
        runtime.project_config.config_project = {"tasks": {"task1": {"a": "b"}}}
        run_click_command(cci.task_doc, runtime=runtime, project=True)
        doc_task.assert_called()
        echo.assert_called()

    @mock.patch("cumulusci.cli.cci.Path")
    @mock.patch("click.echo")
    @mock.patch("cumulusci.cli.cci.doc_task", return_value="docs")
    def test_task_doc_project_write(self, doc_task, echo, Path):
        runtime = mock.Mock()
        runtime.universal_config.tasks = {"test": {}}
        runtime.project_config = BaseProjectConfig(
            runtime.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {"option": {"a": "b"}},
            },
        )
        runtime.project_config.config_project = {"tasks": {"option": {"a": "b"}}}
        run_click_command(cci.task_doc, runtime=runtime, project=True, write=True)
        doc_task.assert_called()
        echo.assert_not_called()

    @mock.patch("cumulusci.cli.cci.rst2ansi")
    @mock.patch("cumulusci.cli.cci.doc_task")
    def test_task_info(self, doc_task, rst2ansi):
        runtime = mock.Mock()
        runtime.project_config.tasks__test = {"options": {}}
        run_click_command(cci.task_info, runtime=runtime, task_name="test")
        doc_task.assert_called_once()
        rst2ansi.assert_called_once()

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_flow_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.get_available_flows.return_value = [
            {"name": "test_flow", "description": "Test Flow", "group": "Testing"}
        ]
        runtime.universal_config.cli__plain_output = None
        run_click_command(cci.flow_list, runtime=runtime, plain=False, print_json=False)

        cli_tbl.assert_called_with(
            [["Flow", "Description"], ["test_flow", "Test Flow"]],
            "Testing",
            wrap_cols=["Description"],
        )

    @mock.patch("json.dumps")
    def test_flow_list_json(self, json_):
        flows = [{"name": "test_flow", "description": "Test Flow"}]
        runtime = mock.Mock()
        runtime.get_available_flows.return_value = flows
        runtime.universal_config.cli__plain_output = None

        run_click_command(cci.flow_list, runtime=runtime, plain=False, print_json=True)

        json_.assert_called_with(flows)

    @mock.patch("click.echo")
    def test_flow_info(self, echo):
        runtime = mock.Mock()
        flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
        runtime.get_flow.return_value = FlowCoordinator(None, flow_config)

        run_click_command(cci.flow_info, runtime=runtime, flow_name="test")

        echo.assert_called_with("Description: Test Flow")

    def test_flow_info__not_found(self):
        runtime = mock.Mock()
        runtime.get_flow.side_effect = FlowNotFoundError
        with self.assertRaises(click.UsageError):
            run_click_command(cci.flow_info, runtime=runtime, flow_name="test")

    @mock.patch("cumulusci.cli.cci.group_items")
    @mock.patch("cumulusci.cli.cci.document_flow")
    def test_flow_doc__no_flows_rst_file(self, doc_flow, group_items):
        runtime = mock.Mock()
        runtime.universal_config.flows = {"test": {}}
        flow_config = FlowConfig({"description": "Test Flow", "steps": {}})
        runtime.get_flow.return_value = FlowCoordinator(None, flow_config)

        group_items.return_value = {"Group One": [["test flow", "description"]]}

        run_click_command(cci.flow_doc, runtime=runtime)
        group_items.assert_called_once()
        doc_flow.assert_called()

    @mock.patch("cumulusci.cli.cci.click.echo")
    @mock.patch("cumulusci.cli.cci.cci_safe_load")
    def test_flow_doc__with_flows_rst_file(self, safe_load, echo):
        runtime = CliRuntime(
            config={
                "flows": {
                    "Flow1": {
                        "steps": {},
                        "description": "Description of Flow1",
                        "group": "Group1",
                    }
                }
            },
            load_keychain=False,
        )

        safe_load.return_value = {
            "intro_blurb": "opening blurb for flow reference doc",
            "groups": {
                "Group1": {"description": "This is a description of group1."},
            },
            "flows": {"Flow1": {"rst_text": "Some ``extra`` **pizzaz**!"}},
        }

        run_click_command(cci.flow_doc, runtime=runtime)

        assert 1 == safe_load.call_count

        expected_call_args = [
            "Flow Reference\n==========================================\n\nopening blurb for flow reference doc\n.. contents::\n    :depth: 2\n    :local:\n\n",
            "Group1\n------",
            "This is a description of group1.",
            "Flow1\n^^^^^\n\n**Description:** Description of Flow1\n\nSome ``extra`` **pizzaz**!\n**Flow Steps**\n\n.. code-block:: console\n",
            "",
        ]
        expected_call_args = [mock.call(s) for s in expected_call_args]
        assert echo.call_args_list == expected_call_args

    def test_flow_run(self):
        org_config = mock.Mock(scratch=True, config={})
        runtime = CliRuntime(
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
        runtime.get_org = mock.Mock(return_value=("test", org_config))
        runtime.get_flow = mock.Mock()

        run_click_command(
            cci.flow_run,
            runtime=runtime,
            flow_name="test",
            org="test",
            delete_org=True,
            debug=False,
            o=[("test_task__color", "blue")],
            skip=(),
            no_prompt=True,
        )

        runtime.get_flow.assert_called_once_with(
            "test", options={"test_task": {"color": "blue"}}
        )
        org_config.delete_org.assert_called_once()

    def test_flow_run_o_error(self):
        org_config = mock.Mock(scratch=True, config={})
        runtime = CliRuntime(config={"noop": {}}, load_keychain=False)
        runtime.get_org = mock.Mock(return_value=("test", org_config))

        with pytest.raises(click.UsageError) as e:
            run_click_command(
                cci.flow_run,
                runtime=runtime,
                flow_name="test",
                org="test",
                delete_org=True,
                debug=False,
                o=[("test_task", "blue")],
                skip=(),
                no_prompt=True,
            )
        assert "-o" in str(e.value)

    def test_flow_run_delete_non_scratch(self):
        org_config = mock.Mock(scratch=False)
        runtime = mock.Mock()
        runtime.get_org.return_value = ("test", org_config)

        with self.assertRaises(click.UsageError):
            run_click_command(
                cci.flow_run,
                runtime=runtime,
                flow_name="test",
                org="test",
                delete_org=True,
                debug=False,
                o=None,
                skip=(),
                no_prompt=True,
            )

    @mock.patch("click.echo")
    def test_flow_run_org_delete_error(self, echo):
        org_config = mock.Mock(scratch=True, config={})
        org_config.delete_org.side_effect = Exception
        org_config.save_if_changed.return_value.__enter__ = lambda *args: ...
        org_config.save_if_changed.return_value.__exit__ = lambda *args: ...
        runtime = CliRuntime(
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
        runtime.get_org = mock.Mock(return_value=("test", org_config))
        DummyTask._run_task = mock.Mock()

        kwargs = {
            "runtime": runtime,
            "flow_name": "test",
            "org": "test",
            "delete_org": True,
            "debug": False,
            "no_prompt": True,
            "o": (("test_task__color", "blue"),),
            "skip": (),
        }

        run_click_command(cci.flow_run, **kwargs)

        echo.assert_any_call(
            "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
        )

    @mock.patch(
        "cumulusci.cli.runtime.CliRuntime.get_org",
        lambda *args, **kwargs: (MagicMock(), MagicMock()),
    )
    @mock.patch("cumulusci.core.runtime.BaseCumulusCI._load_keychain", MagicMock())
    @mock.patch("pdb.post_mortem", MagicMock())
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr", MagicMock())
    @mock.patch("cumulusci.cli.cci.init_logger", MagicMock())
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    def test_run_task_debug(self, get_tempfile_logger):
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")

        gipnew = "cumulusci.tasks.preflight.packages.GetInstalledPackages._run_task"
        with mock.patch(gipnew, mock_validate_debug(False)):
            cci.main(["cci", "task", "run", "get_installed_packages"])
        with mock.patch(gipnew, mock_validate_debug(True)):
            cci.main(["cci", "task", "run", "get_installed_packages", "--debug"])

    @mock.patch(
        "cumulusci.cli.runtime.CliRuntime.get_org",
        lambda *args, **kwargs: (MagicMock(), MagicMock()),
    )
    @mock.patch("cumulusci.core.runtime.BaseCumulusCI._load_keychain", MagicMock())
    @mock.patch("pdb.post_mortem", MagicMock())
    @mock.patch("cumulusci.cli.cci.tee_stdout_stderr", MagicMock())
    @mock.patch("cumulusci.cli.cci.init_logger", MagicMock())
    @mock.patch("cumulusci.tasks.robotframework.RobotLibDoc", MagicMock())
    @mock.patch("cumulusci.cli.cci.get_tempfile_logger")
    def test_run_flow_debug(self, get_tempfile_logger):
        get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")
        rtd = "cumulusci.tasks.robotframework.RobotTestDoc._run_task"

        with mock.patch(rtd, mock_validate_debug(False)):
            cci.main(["cci", "flow", "run", "robot_docs"])
        with mock.patch(rtd, mock_validate_debug(True)):
            cci.main(["cci", "flow", "run", "robot_docs", "--debug"])


def validate_service(options):
    raise Exception("Validation failed")


class SetTrace(Exception):
    pass


def mock_validate_debug(value):
    def _run_task(self, *args, **kwargs):
        assert bool(self.debug_mode) == bool(value)

    return _run_task
