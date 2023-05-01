import contextlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path
from unittest import mock

import click
import pkg_resources
import pytest
from requests.exceptions import ConnectionError
from rich.console import Console

import cumulusci
from cumulusci.cli import cci
from cumulusci.cli.tests.utils import run_click_command
from cumulusci.cli.utils import get_installed_version
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.utils import temporary_dir

MagicMock = mock.MagicMock()
CONSOLE = mock.Mock()


@pytest.fixture(autouse=True)
def env_config():
    config = {
        "global_tempdir": tempfile.gettempdir(),
        "tempdir": tempfile.mkdtemp(),
        "environ_mock": mock.patch.dict(
            os.environ, {"HOME": tempfile.mkdtemp(), "CUMULUSCI_KEY": ""}
        ),
    }
    # setup
    config["environ_mock"].start()
    assert config["global_tempdir"] in os.environ["HOME"]
    yield config
    # tear down
    assert config["global_tempdir"] in os.environ["HOME"]
    config["environ_mock"].stop()
    shutil.rmtree(config["tempdir"])


@mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.init_logger")
@mock.patch("cumulusci.cli.cci.check_latest_version")
@mock.patch("cumulusci.cli.cci.CliRuntime")
@mock.patch("cumulusci.cli.cci.cli")
def test_main(
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
    init_logger.assert_called_once_with(debug=True)
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
    post_mortem,
    cli,
    CliRuntime,
    check_latest_version,
    init_logger,
    get_tempfile_logger,
    tee,
    capsys,
):
    runtime = mock.Mock()
    runtime.universal_config.cli__show_stacktraces = True
    CliRuntime.return_value = runtime
    cli.side_effect = Exception
    get_tempfile_logger.return_value = (mock.Mock(), "tempfile.log")

    with pytest.raises(SystemExit):
        cci.main(["cci"])

    check_latest_version.assert_called_once()
    init_logger.assert_called_once_with(debug=False)
    CliRuntime.assert_called_once()
    cli.assert_called_once()
    post_mortem.assert_not_called()
    captured = capsys.readouterr()
    assert "Traceback (most recent call last)" in captured.err


@mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.init_logger")
@mock.patch("cumulusci.cli.cci.cli")
@mock.patch("sys.exit")
def test_main__abort(
    sys_exit, cli, init_logger, get_tempfile_logger, tee_stdout_stderr
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
    init_logger.assert_called_once_with(debug=False)
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
def test_main__CliRuntime_error(CliRuntime, get_tempfile_logger, tee):
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
    CliRuntime, tee_stdout_stderr, get_tempfile_logger, init_logger
):

    # get_tempfile_logger doesn't clean up after itself which breaks other tests
    get_tempfile_logger.return_value = mock.Mock(), ""

    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        cci.main(["cci", "org", "default", "xyzzy"])
    assert "xyzzy is now the default org" in stdout.getvalue()

    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        cci.main(["cci", "org", "default", "--org", "xyzzy2"])
    assert "xyzzy2 is now the default org" in stdout.getvalue()

    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.main(["cci", "org", "default", "xyzzy1", "--org", "xyzzy2"])
    assert "not both" in stderr.getvalue()

    CliRuntime().keychain.get_default_org.return_value = ("xyzzy3", None)

    # cci org remove should really need an attached org
    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.main(["cci", "org", "remove"])
    assert "Please specify ORGNAME or --org ORGNAME" in stderr.getvalue()


@mock.patch("cumulusci.cli.cci.init_logger")  # side effects break other tests
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
@mock.patch("sys.exit")
@mock.patch("cumulusci.cli.cci.CliRuntime")
def test_cci_org_default__no_orgname(
    CliRuntime, exit, tee_stdout_stderr, get_tempfile_logger, init_logger
):
    # get_tempfile_logger doesn't clean up after itself which breaks other tests
    get_tempfile_logger.return_value = mock.Mock(), ""

    CliRuntime().keychain.get_default_org.return_value = ("xyzzy4", None)
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        cci.main(["cci", "org", "default"])
    assert "xyzzy4 is the default org" in stdout.getvalue()

    CliRuntime().keychain.get_default_org.return_value = (None, None)
    with contextlib.redirect_stdout(io.StringIO()) as stdout:
        cci.main(["cci", "org", "default"])
    assert "There is no default org" in stdout.getvalue()


DEPLOY_CLASS_PATH = f"cumulusci.tasks.salesforce.Deploy{'.Deploy' if sys.version_info >= (3, 11) else ''}"


@mock.patch("cumulusci.cli.cci.init_logger", mock.Mock())
@mock.patch("cumulusci.cli.cci.tee_stdout_stderr", mock.MagicMock())
@mock.patch(f"{DEPLOY_CLASS_PATH}.__call__", mock.Mock())
@mock.patch("sys.exit", mock.Mock())
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.CliRuntime")
@mock.patch(f"{DEPLOY_CLASS_PATH}.__init__")
def test_cci_run_task_options__with_dash(
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
            "tasks": {"deploy": {"class_path": "cumulusci.tasks.salesforce.Deploy"}},
        },
    )

    cci.main(
        ["cci", "task", "run", "deploy", "--path", "x", "--clean-meta-xml", "False"]
    )
    task_config = Deploy.mock_calls[0][1][1]
    assert "clean_meta_xml" in task_config.options


@mock.patch("cumulusci.cli.cci.init_logger", mock.Mock())
@mock.patch("cumulusci.cli.cci.tee_stdout_stderr", mock.MagicMock())
@mock.patch(f"{DEPLOY_CLASS_PATH}.__call__", mock.Mock())
@mock.patch("sys.exit", mock.Mock())
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.CliRuntime")
@mock.patch(f"{DEPLOY_CLASS_PATH}.__init__")
def test_cci_run_task_options__old_style_with_dash(
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
            "tasks": {"deploy": {"class_path": "cumulusci.tasks.salesforce.Deploy"}},
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
def test_handle_exception(traceback, cci_open):
    console = mock.Mock()
    Console.return_value = console
    error_message = "foo"
    cci_open.__enter__.return_value = mock.Mock()

    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.handle_exception(error_message, False, "logfile.path")

    stderr = stderr.getvalue()
    assert f"Error: {error_message}" in stderr
    assert cci.SUGGEST_ERROR_COMMAND in stderr
    traceback.print_exc.assert_called_once()


@mock.patch("cumulusci.cli.cci.open")
def test_handle_exception__error_cmd(cci_open):
    """Ensure we don't write to logfiles when running `cci error ...` commands."""
    error_message = "foo"
    logfile_path = None

    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.handle_exception(error_message, False, logfile_path)

    stderr = stderr.getvalue()
    assert f"Error: {error_message}" in stderr
    assert cci.SUGGEST_ERROR_COMMAND in stderr
    cci_open.assert_not_called()


@mock.patch("cumulusci.cli.cci.open")
@mock.patch("cumulusci.cli.cci.traceback")
def test_handle_click_exception(traceback, cci_open):
    cci_open.__enter__.return_value = mock.Mock()

    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.handle_exception(click.ClickException("[oops]"), False, "file.path")

    stderr = stderr.getvalue()
    assert "Error: [oops]" in stderr
    traceback.assert_not_called()


@mock.patch("cumulusci.cli.cci.open")
def test_handle_connection_exception(cci_open):
    cci_open.__enter__.return_value = mock.Mock()

    with contextlib.redirect_stderr(io.StringIO()) as stderr:
        cci.handle_exception(ConnectionError(), False, "file.log")

    stderr = stderr.getvalue()
    assert "We encountered an error with your internet connection." in stderr


def test_cli():
    run_click_command(cci.cli)


@mock.patch(
    "cumulusci.cli.cci.get_latest_final_version",
    mock.Mock(return_value=pkg_resources.parse_version("100")),
)
def test_version(capsys):
    run_click_command(cci.version)
    console_output = capsys.readouterr().out
    assert f"CumulusCI version: {cumulusci.__version__}" in console_output
    assert "There is a newer version of CumulusCI available" in console_output


@mock.patch(
    "cumulusci.cli.cci.get_latest_final_version",
    mock.Mock(return_value=pkg_resources.parse_version("1")),
)
def test_version__latest(capsys):
    run_click_command(cci.version)
    console_output = capsys.readouterr().out
    assert "You have the latest version of CumulusCI" in console_output


@mock.patch("cumulusci.cli.cci.warn_if_no_long_paths")
@mock.patch("cumulusci.cli.cci.get_latest_final_version", get_installed_version)
def test_version__win_path_warning(warn_if):
    run_click_command(cci.version)
    warn_if.assert_called_once()


@mock.patch("code.interact")
def test_shell(interact):
    run_click_command(cci.shell)
    interact.assert_called_once()
    assert "config" in interact.call_args[1]["local"]
    assert "runtime" in interact.call_args[1]["local"]


@mock.patch("runpy.run_path")
def test_shell_script(runpy):
    run_click_command(cci.shell, script="foo.py")
    runpy.assert_called_once()
    assert "config" in runpy.call_args[1]["init_globals"]
    assert "runtime" in runpy.call_args[1]["init_globals"]
    assert runpy.call_args[0][0] == "foo.py", runpy.call_args[0]


@mock.patch("builtins.print")
def test_shell_code(print):
    run_click_command(cci.shell, python="print(config, runtime)")
    print.assert_called_once()


@mock.patch("cumulusci.cli.cci.print")
def test_shell_mutually_exclusive_args(print):
    with pytest.raises(Exception) as e:
        run_click_command(cci.shell, script="foo.py", python="print(config, runtime)")
    assert "Cannot specify both" in e.value.message


@mock.patch("code.interact")
def test_shell__no_project(interact):
    with temporary_dir():
        run_click_command(cci.shell)
        interact.assert_called_once()


def test_cover_command_groups():
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
def test_run_task_debug(get_tempfile_logger):
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
def test_run_flow_debug(get_tempfile_logger):
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


@mock.patch("cumulusci.cli.cci.tee_stdout_stderr")
@mock.patch("cumulusci.cli.cci.get_tempfile_logger")
@mock.patch("cumulusci.cli.cci.init_logger")
@mock.patch("cumulusci.cli.cci.check_latest_version")
@mock.patch("cumulusci.cli.cci.CliRuntime")
@mock.patch("cumulusci.cli.cci.show_version_info")
def test_dash_dash_version(
    show_version_info,
    CliRuntime,
    check_latest_version,
    init_logger,
    get_tempfile_logger,
    tee,
):
    get_tempfile_logger.return_value = mock.Mock(), "tempfile.log"
    cci.main(["cci", "--help"])
    assert len(show_version_info.mock_calls) == 0

    cci.main(["cci", "version"])
    assert len(show_version_info.mock_calls) == 1

    cci.main(["cci", "--version"])
    assert len(show_version_info.mock_calls) == 2
