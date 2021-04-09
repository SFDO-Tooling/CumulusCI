from unittest import mock
import json
import time

import pkg_resources
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
    assert "1.0.1" == result.base_version


@mock.patch("cumulusci.cli.utils.get_installed_version")
@mock.patch("cumulusci.cli.utils.get_latest_final_version")
@mock.patch("cumulusci.cli.utils.click")
def test_check_latest_version(click, get_latest_final_version, get_installed_version):
    with utils.timestamp_file() as f:
        f.write(str(time.time() - 4000))
    get_latest_final_version.return_value = pkg_resources.parse_version("2")
    get_installed_version.return_value = pkg_resources.parse_version("1")

    utils.check_latest_version()

    click.echo.assert_called_once()


@mock.patch("cumulusci.cli.utils.get_latest_final_version")
@mock.patch("cumulusci.cli.utils.click")
def test_check_latest_version_request_error(click, get_latest_final_version):
    with utils.timestamp_file() as f:
        f.write(str(time.time() - 4000))
    get_latest_final_version.side_effect = requests.exceptions.RequestException()

    utils.check_latest_version()

    click.echo.assert_any_call("Error checking cci version:", err=True)
