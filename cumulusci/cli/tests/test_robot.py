import sys
from unittest import mock

import click.exceptions
import pytest

from cumulusci.cli import cci

from .utils import run_cli_command


@mock.patch("sys.exit")
def test_bogus_subcommand(sys_exit):
    cci.main(["cci", "robot", "bogus"])
    sys_exit.assert_called_once_with(1)


@mock.patch("cumulusci.cli.robot.sarge")
def test_no_npm(sarge):
    """Verify the error message we emit when npm --version throws an error"""

    sarge.Command.side_effect = mock_Command(returncodes={"npm --version": 1})
    with pytest.raises(
        click.exceptions.ClickException, match="Unable to find a usable npm.*"
    ):
        run_cli_command("robot", "install_playwright", "-n")
    sarge.Command.assert_called_once_with("npm --version", shell=True)


@mock.patch("cumulusci.cli.robot.sarge")
def test_playwright_already_installed(sarge):

    sarge.Command.side_effect = mock_Command()
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=True):
        result = run_cli_command("robot", "install_playwright", "--dry_run")
        assert (
            result.output == "Playwright support seems to already have been installed\n"
        )


@mock.patch("cumulusci.cli.robot.sarge")
def test_happy_path(sarge):

    sarge.Command.side_effect = mock_Command()
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        run_cli_command("robot", "install_playwright")
        sarge.Command.assert_has_calls(
            [
                mock.call("npm --version", shell=True),
                mock.call(
                    [sys.executable, "-m", "pip", "install", "robotframework-browser"],
                    shell=False,
                ),
                mock.call([sys.executable, "-m", "Browser.entry", "init"], shell=False),
            ]
        )


@mock.patch("cumulusci.cli.robot.sarge")
def test_uninstall_playwright(sarge):

    sarge.Command.side_effect = mock_Command()
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        run_cli_command("robot", "uninstall_playwright")
        sarge.Command.assert_has_calls(
            [
                mock.call([sys.executable, "-m", "Browser.entry", "clean-node"]),
                mock.call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "uninstall",
                        "robotframework-browser",
                        "--yes",
                    ],
                ),
            ]
        )


def mock_Command(returncodes={}):
    """Create a mock for sarge.Command

    returncodes is a dictionary of commands as keys
    and returncodes as values, so we can control which
    command line tools act like they pass or fail.

    By default, every command will return zero unless
    explicitly told to exit with something else.
    """

    def the_real_mock(cmd, **kwargs):
        the_mock = mock.Mock()
        the_mock.args = cmd

        def run():
            returncode = returncodes.get(str(cmd), 0)
            the_mock.returncode = returncode

        the_mock.run.side_effect = run
        return the_mock

    return the_real_mock
