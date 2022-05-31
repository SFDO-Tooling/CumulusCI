import json
import sys
import time
from unittest import mock

import pkg_resources
import pytest
import requests
import responses

import cumulusci

from .. import utils


def test_get_installed_version():
    result = utils.get_installed_version()
    assert cumulusci.__version__ == str(result)


@responses.activate
def test_get_latest_final_version():
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
    result = utils.get_latest_final_version()
    assert result.base_version == "1.0.1"


@mock.patch("cumulusci.cli.utils.get_installed_version")
@mock.patch("cumulusci.cli.utils.get_latest_final_version")
@mock.patch("cumulusci.cli.utils.click")
def test_check_latest_version(click, get_latest_final_version, get_installed_version):
    with utils.timestamp_file() as f:
        f.write(str(time.time() - 4000))
    get_latest_final_version.return_value = pkg_resources.parse_version("2")
    get_installed_version.return_value = pkg_resources.parse_version("1")

    utils.check_latest_version()
    if sys.version_info > utils.LOWEST_SUPPORTED_VERSION:
        click.echo.assert_called_once()
    else:
        click.echo.assert_called()


@mock.patch("cumulusci.cli.utils.get_latest_final_version")
@mock.patch("cumulusci.cli.utils.click")
def test_check_latest_version_request_error(click, get_latest_final_version):
    with utils.timestamp_file() as f:
        f.write(str(time.time() - 4000))
    get_latest_final_version.side_effect = requests.exceptions.RequestException()

    utils.check_latest_version()

    click.echo.assert_any_call("Error checking cci version:", err=True)


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Requires Windows Registry"
)
@mock.patch("winreg.QueryValueEx")
def test_win32_warning(query_value):
    query_value.return_value = (1, 1)

    is_enabled = utils.win32_long_paths_enabled()

    query_value.assert_called_once()
    assert "LongPathsEnabled" in query_value.call_args.args
    assert is_enabled


@pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Should not print on non-win32"
)
@mock.patch("cumulusci.cli.utils.win32_long_paths_enabled")
@mock.patch("rich.console.Console.print")
def test_no_longpath_warn_on_posix(console_print, is_enabled):
    utils.warn_if_no_long_paths()

    is_enabled.assert_not_called()
    console_print.assert_not_called()


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Requires Windows Registry"
)
@mock.patch("cumulusci.cli.utils.win32_long_paths_enabled")
@mock.patch("rich.console.Console.print")
def test_no_longpath_warn_on_win(console_print, is_enabled):
    is_enabled.return_value = True

    utils.warn_if_no_long_paths()

    is_enabled.assert_called_once()
    console_print.assert_not_called()


@pytest.mark.skipif(
    not sys.platform.startswith("win"), reason="Requires Windows Registry"
)
@mock.patch("cumulusci.cli.utils.win32_long_paths_enabled")
@mock.patch("rich.console.Console.print")
def test_longpath_warn_on_win(console_print, is_enabled):
    is_enabled.return_value = False

    utils.warn_if_no_long_paths()

    is_enabled.assert_called_once()
    console_print.assert_called_once_with(utils.WIN_LONG_PATH_WARNING)
