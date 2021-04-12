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
        # no assertion; this test is for coverage of empty methods

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


def mock_validate_debug(value):
    def _run_task(self, *args, **kwargs):
        assert bool(self.debug_mode) == bool(value)

    return _run_task
