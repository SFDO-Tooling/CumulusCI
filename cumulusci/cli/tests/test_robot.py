import sys
from unittest import mock

import click.exceptions
import pytest

from cumulusci.cli.robot import _is_package_installed

from .utils import run_cli_command


class MockDistribution:
    """Mocks an importlib.metadata.Distribution object"""

    def __init__(self, name):
        self.name = name


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


@mock.patch("cumulusci.cli.robot.importlib.metadata.distribution")
def test_is_package_installed(mock_distribution):
    """Verify that the helper _is_package_installed returns the correct result"""
    # Test when package is installed
    mock_distribution.return_value = MockDistribution("robotframework-browser")
    result = _is_package_installed("robotframework-browser")
    assert result is True

    # Test when package is not installed
    from importlib.metadata import PackageNotFoundError

    mock_distribution.side_effect = PackageNotFoundError("Package not found")
    result = _is_package_installed("robotframework-browser")
    assert result is False


@mock.patch("cumulusci.cli.robot.sarge")
def test_happy_path(sarge):
    """Verify the happy path is indeed happy"""
    sarge.Command.side_effect = mock_Command()
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        run_cli_command("robot", "install_playwright")
        actual_calls = [call.args[0] for call in sarge.Command.mock_calls]
        expected_calls = [
            "npm --version",
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "robotframework-browser",
            ],
            [sys.executable, "-m", "Browser.entry", "init"],
        ]
        msg = f"\n-- expected --\n{expected_calls}\n\n-- actual --\n{actual_calls}"

        assert actual_calls == expected_calls, msg


@mock.patch("sys.exit")
def test_bogus_subcommand(sys_exit):
    """Verify a bogus subcommand returns a UsageError"""
    with pytest.raises(click.exceptions.UsageError, match="No such command 'bogus'"):
        run_cli_command("robot", "bogus")


@mock.patch("cumulusci.cli.robot.sarge")
def test_no_npm(sarge):
    """Verify the error message we emit when npm --version throws an error"""

    sarge.Command.side_effect = mock_Command(returncodes={"npm --version": 1})
    with pytest.raises(
        click.exceptions.ClickException, match="Unable to find a usable npm.*"
    ):
        run_cli_command("robot", "install_playwright", "--dry_run")
    sarge.Command.assert_called_once()
    assert sarge.Command.mock_calls[0].args[0] == "npm --version"


@mock.patch("cumulusci.cli.robot.sarge")
def test_playwright_dry_run(sarge):
    """Verify the output of a dry run"""
    sarge.Command.side_effect = mock_Command(returncodes={"npm --version": 0})
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        result = run_cli_command("robot", "install_playwright", "--dry_run")
        expected_output = "\n".join(
            [
                "installing robotframework-browser ...",
                f"would run {sys.executable} -m pip install robotframework-browser",
                f"would run {sys.executable} -m Browser.entry init\n",
            ]
        )
        msg = f"\n-- expected --\n{expected_output}\n\n-- actual --\n{result.output}"
        assert result.output == expected_output, msg


@mock.patch("cumulusci.cli.robot.sarge")
def test_playwright_failure_to_initialize_browser_library(sarge):
    """Verify we raise an exception if we can't initialize the browser library"""
    cmd = str([sys.executable, "-m", "Browser.entry", "init"])
    sarge.Command.side_effect = mock_Command(returncodes={cmd: 1})
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        with pytest.raises(
            click.exceptions.ClickException,
            match="unable to initialize browser library",
        ):
            run_cli_command("robot", "install_playwright")


@mock.patch("cumulusci.cli.robot.sarge")
def test_playwright_failure_to_install_browser_library(sarge):
    """Verify we raise an exception if we can't install playwright"""
    cmd = str([sys.executable, "-m", "pip", "install", "robotframework-browser"])
    sarge.Command.side_effect = mock_Command(returncodes={cmd: 1})
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=False):
        with pytest.raises(
            click.exceptions.ClickException,
            match="robotframework-browser was not installed",
        ):
            run_cli_command("robot", "install_playwright")


@mock.patch("cumulusci.cli.robot.sarge")
def test_playwright_already_installed(sarge):
    """Verify we exit early if the package is already installed"""
    sarge.Command.side_effect = mock_Command()
    with mock.patch("cumulusci.cli.robot._is_package_installed", return_value=True):
        result = run_cli_command("robot", "install_playwright", "--dry_run")
        assert (
            result.output == "Playwright support seems to already have been installed\n"
        )


@mock.patch("cumulusci.cli.robot.sarge")
def test_uninstall_playwright(sarge):
    """Verify calling 'robot uninstall_playwright' calls the right utilities"""
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
