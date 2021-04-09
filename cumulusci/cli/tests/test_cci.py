import io
import os
import shutil
import tempfile
import pytest
import unittest
from pathlib import Path
import contextlib

import click
from unittest import mock
import pkg_resources
from requests.exceptions import ConnectionError

import cumulusci
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.cli import cci
from cumulusci.utils import temporary_dir
from cumulusci.cli.tests.utils import run_click_command

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
    def test_service_list__no_active_defaults(self, cli_tbl):
        runtime = mock.Mock()
        runtime.project_config.services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
            "something_else": {"description": "something else"},
        }
        runtime.keychain.list_services.return_value = {
            "test": ["test_alias", "test2_alias"],
            "bad": ["bad_alias"],
        }
        runtime.keychain._default_services = {"test": "test_alias"}
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=False
        )

        cli_tbl.assert_called_with(
            [
                ["Type", "Name", "Default", "Description"],
                ["bad", "bad_alias", False, "Unconfigured Service"],
                ["something_else", "", False, "something else"],
                ["test", "test_alias", True, "Test Service"],
                ["test", "test2_alias", False, "Test Service"],
            ],
            bool_cols=["Default"],
            dim_rows=[2],
            title="Services",
            wrap_cols=["Description"],
        )

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_list(self, cli_tbl):
        runtime = mock.Mock()
        runtime.project_config.services = {
            "bad": {"description": "Unconfigured Service"},
            "test": {"description": "Test Service"},
            "something_else": {"description": "something else"},
        }
        runtime.keychain.list_services.return_value = {
            "test": ["test_alias", "test2_alias"],
            "bad": ["bad_alias"],
        }
        runtime.keychain._default_services = {"test": "test_alias", "bad": "bad_alias"}
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_list, runtime=runtime, plain=False, print_json=False
        )

        cli_tbl.assert_called_with(
            [
                ["Type", "Name", "Default", "Description"],
                ["bad", "bad_alias", True, "Unconfigured Service"],
                ["something_else", "", False, "something else"],
                ["test", "test_alias", True, "Test Service"],
                ["test", "test2_alias", False, "Test Service"],
            ],
            bool_cols=["Default"],
            dim_rows=[2],
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

    def test_service_connect__list_commands(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config.services = {"test": {}}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            result = multi_cmd.list_commands(ctx)
        assert result == ["test"]

    def test_service_connect__list_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.Mock()
        runtime.project_config = None
        runtime.universal_config.services = {"test": {}}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            result = multi_cmd.list_commands(ctx)
        assert result == ["test"]

    def test_service_connect(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(ctx.obj, project=True, service_name="test-alias")

            runtime.keychain.set_service.assert_called_once()

            cmd.callback(ctx.obj, project=False, service_name="test-alias")

    @mock.patch("cumulusci.cli.cci.click.confirm")
    def test_service_connect__alias_already_exists(self, confirm):
        confirm.side_effect = "y"
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test-type": {"attributes": {"attr": {"required": False}}}
        }
        runtime.services = {"test-type": {"already-exists": "some config"}}
        runtime.keychain.list_services.return_value = {"test-type": ["already-exists"]}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test-type")
            cmd.callback(
                runtime,
                service_type="test-type",
                service_name="already-exists",
                project=True,
            )

        confirm.assert_called_once()

    @mock.patch("click.echo")
    def test_service_connect__global_default(self, echo):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(
                runtime, service_name="test-alias", default=True, project=False
            )

        runtime.keychain.set_default_service.assert_called_once_with(
            "test", "test-alias", project=False
        )
        assert (
            echo.call_args_list[0][0][0] == "Service test:test-alias is now connected"
        )
        assert (
            echo.call_args_list[1][0][0]
            == "Service test:test-alias is now the default for all CumulusCI projects"
        )

    @mock.patch("click.echo")
    def test_service_connect__project_default(self, echo):
        multi_cmd = cci.ConnectServiceCommand()
        ctx = mock.Mock()
        runtime = mock.MagicMock()
        runtime.project_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(
                runtime, service_name="test-alias", default=False, project=True
            )

        runtime.keychain.set_default_service.assert_called_once_with(
            "test", "test-alias", project=True
        )
        assert (
            echo.call_args_list[0][0][0] == "Service test:test-alias is now connected"
        )
        assert (
            "Service test:test-alias is now the default for project"
            in echo.call_args_list[1][0][0]
        )

    def test_service_connect_global_keychain(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config = None
        runtime.universal_config.services = {
            "test": {"attributes": {"attr": {"required": False}}}
        }

        with click.Context(multi_cmd, obj=runtime) as ctx:
            cmd = multi_cmd.get_command(ctx, "test")
            cmd.callback(ctx.obj, project=True, service_name="test-alias")

            runtime.keychain.set_service.assert_called_once()

            cmd.callback(ctx.obj, project=False, service_name="test-alias")

    def test_service_connect_invalid_service(self):
        multi_cmd = cci.ConnectServiceCommand()
        runtime = mock.MagicMock()
        runtime.project_config.services = {}

        with click.Context(multi_cmd, obj=runtime) as ctx:
            with pytest.raises(click.UsageError):
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
                cmd.callback(
                    runtime,
                    service_type="test",
                    service_name="test-alias",
                    project=False,
                )

    @mock.patch("cumulusci.cli.cci.CliTable")
    def test_service_info(self, cli_tbl):
        cli_tbl._table = mock.Mock()
        service_config = mock.Mock()
        service_config.config = {"description": "Test Service"}
        runtime = mock.Mock()
        runtime.keychain.get_service.return_value = service_config
        runtime.universal_config.cli__plain_output = None

        run_click_command(
            cci.service_info,
            runtime=runtime,
            service_type="test",
            service_name="test-alias",
            plain=False,
        )

        cli_tbl.assert_called_with(
            [["Key", "Value"], ["\x1b[1mdescription\x1b[0m", "Test Service"]],
            title="test/test-alias",
            wrap_cols=["Value"],
        )

    @mock.patch("click.echo")
    def test_service_info_not_configured(self, echo):
        runtime = mock.Mock()
        runtime.keychain.get_service.side_effect = ServiceNotConfigured

        run_click_command(
            cci.service_info,
            runtime=runtime,
            service_type="test",
            service_name="test-alias",
            plain=False,
        )
        assert "not configured for this project" in echo.call_args[0][0]

    @mock.patch("click.echo")
    def test_service_default__global(self, echo):
        runtime = mock.Mock()
        run_click_command(
            cci.service_default,
            runtime=runtime,
            service_type="test",
            service_name="test-alias",
            project=False,
        )
        runtime.keychain.set_default_service.called_once_with("test", "test-alias")
        echo.assert_called_once_with(
            "Service test:test-alias is now the default for all CumulusCI projects"
        )

    @mock.patch("click.echo")
    def test_service_default__project(self, echo):
        runtime = mock.Mock()
        runtime.keychain.project_local_dir = "test"
        run_click_command(
            cci.service_default,
            runtime=runtime,
            service_type="test",
            service_name="test-alias",
            project=True,
        )
        runtime.keychain.set_default_service.called_once_with("test", "test-alias")
        echo.assert_called_once_with(
            "Service test:test-alias is now the default for project 'test'"
        )

    @mock.patch("click.echo")
    def test_service_default__exception(self, echo):
        runtime = mock.Mock()
        runtime.keychain.set_default_service.side_effect = ServiceNotConfigured(
            "test error"
        )
        run_click_command(
            cci.service_default,
            runtime=runtime,
            service_type="no-such-type",
            service_name="test-alias",
            project=False,
        )
        echo.assert_called_once_with(
            "An error occurred setting the default service: test error"
        )

    @mock.patch("click.echo")
    def test_service_rename(self, echo):
        runtime = mock.Mock()
        run_click_command(
            cci.service_rename,
            runtime=runtime,
            service_type="test-type",
            current_name="old-alias",
            new_name="new-alias",
        )
        runtime.keychain.rename_service.assert_called_once_with(
            "test-type", "old-alias", "new-alias"
        )
        echo.assert_called_once_with(
            "Service test-type:old-alias has been renamed to new-alias"
        )

    @mock.patch("click.echo")
    def test_service_rename__exception(self, echo):
        runtime = mock.Mock()
        runtime.keychain.rename_service.side_effect = ServiceNotConfigured("test error")
        run_click_command(
            cci.service_rename,
            runtime=runtime,
            service_type="test-type",
            current_name="old-alias",
            new_name="new-alias",
        )
        echo.assert_called_once_with(
            "An error occurred renaming the service: test error"
        )

    @mock.patch("cumulusci.cli.cci.click")
    def test_service_remove(self, click):
        click.prompt.side_effect = ("future-default-alias",)
        runtime = mock.Mock()
        runtime.keychain.services = {
            "github": {
                "current-default-alias": "config1",
                "another-alias": "config2",
                "future-default-alias": "config3",
            }
        }
        runtime.keychain._default_services = {"github": "current-default-alias"}
        runtime.keychain.list_services.return_value = {
            "github": ["current-default-alias", "another-alias", "future-default-alias"]
        }
        run_click_command(
            cci.service_remove,
            runtime=runtime,
            service_type="github",
            service_name="current-default-alias",
        )
        runtime.keychain.remove_service.assert_called_once_with(
            "github", "current-default-alias"
        )
        runtime.keychain.set_default_service.assert_called_once_with(
            "github", "future-default-alias"
        )
        assert (
            click.echo.call_args_list[-1][0][0]
            == "Service github:current-default-alias has been removed."
        )

    @mock.patch("cumulusci.cli.cci.click")
    def test_service_remove__name_does_not_exist(self, click):
        click.prompt.side_effect = ("this-alias-does-not-exist",)
        runtime = mock.Mock()
        runtime.keychain.services = {
            "github": {
                "current-default-alias": "config1",
                "another-alias": "config2",
                "future-default-alias": "config3",
            }
        }
        runtime.keychain._default_services = {"github": "current-default-alias"}
        runtime.keychain.list_services.return_value = {
            "github": ["current-default-alias", "another-alias", "future-default-alias"]
        }
        run_click_command(
            cci.service_remove,
            runtime=runtime,
            service_type="github",
            service_name="current-default-alias",
        )
        assert (
            click.echo.call_args_list[-1][0][0]
            == "No service of type github with name: this-alias-does-not-exist"
        )
        assert runtime.keychain.remove_service.call_count == 0
        assert runtime.keychain.set_default_service.call_count == 0

    @mock.patch("cumulusci.cli.cci.click")
    def test_service_remove__exception_thrown(self, click):

        click.prompt.side_effect = ("future-default-alias",)
        runtime = mock.Mock()
        runtime.keychain.services = {
            "github": {
                "current-default-alias": "config1",
                "another-alias": "config2",
                "future-default-alias": "config3",
            }
        }
        runtime.keychain._default_services = {"github": "current-default-alias"}
        runtime.keychain.list_services.return_value = {
            "github": ["current-default-alias", "another-alias", "future-default-alias"]
        }
        runtime.keychain.remove_service.side_effect = ServiceNotConfigured("test error")
        run_click_command(
            cci.service_remove,
            runtime=runtime,
            service_type="github",
            service_name="current-default-alias",
        )
        assert (
            click.echo.call_args_list[-1][0][0]
            == "An error occurred removing the service: test error"
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


def mock_validate_debug(value):
    def _run_task(self, *args, **kwargs):
        assert bool(self.debug_mode) == bool(value)

    return _run_task
