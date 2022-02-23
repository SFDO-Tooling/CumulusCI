import contextlib
import os
import re
import sys
import time
from collections import defaultdict

import click
import pkg_resources
import requests
from rich.console import Console

from cumulusci import __version__
from cumulusci.core.config import UniversalConfig
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.http.requests_utils import safe_json_from_response

LOWEST_SUPPORTED_VERSION = (3, 8, 0)
WIN_LONG_PATH_WARNING = """
WARNING: Long path support is not enabled. This can lead to errors with some
tasks. Your administrator will need to activate the "Enable Win32 long paths"
group policy, or set LongPathsEnabled to 1 in the registry key
HKEY_LOCAL_MACHINE\\SYSTEM\\CurrentControlSet\\Control\\FileSystem.
"""


def group_items(items):
    """Given a list of dicts with 'group' keys,
    returns those items in lists categorized group"""
    groups = defaultdict(list)
    for item in items:
        group_name = item["group"] or "Other"
        groups[group_name].append([item["name"], item["description"]])

    return groups


@contextlib.contextmanager
def timestamp_file():
    """Opens a file for tracking the time of the last version check"""

    config_dir = UniversalConfig.default_cumulusci_dir()
    timestamp_file = os.path.join(config_dir, "cumulus_timestamp")

    try:
        with open(timestamp_file, "r+") as f:
            yield f
    except IOError:  # file does not exist
        with open(timestamp_file, "w+") as f:
            yield f


FINAL_VERSION_RE = re.compile(r"^[\d\.]+$")


def is_final_release(version: str) -> bool:
    """Returns bool whether version string should be considered a final release.

    cumulusci versions are considered final if they contain only digits and periods.
    e.g. 1.0.1 is final but 2.0b1 and 2.0.dev0 are not.
    """
    return bool(FINAL_VERSION_RE.match(version))


def get_latest_final_version():
    """return the latest version of cumulusci in pypi, be defensive"""
    # use the pypi json api https://wiki.python.org/moin/PyPIJSON
    res = safe_json_from_response(
        requests.get("https://pypi.org/pypi/cumulusci/json", timeout=5)
    )
    with timestamp_file() as f:
        f.write(str(time.time()))
    versions = []
    for versionstring in res["releases"].keys():
        if not is_final_release(versionstring):
            continue
        versions.append(pkg_resources.parse_version(versionstring))
    versions.sort(reverse=True)
    return versions[0]


def check_latest_version():
    """checks for the latest version of cumulusci from pypi, max once per hour"""
    check = True

    with timestamp_file() as f:
        timestamp = float(f.read() or 0)
    delta = time.time() - timestamp
    check = delta > 3600

    if check:
        try:
            latest_version = get_latest_final_version()
        except requests.exceptions.RequestException as e:
            click.echo("Error checking cci version:", err=True)
            click.echo(str(e), err=True)
            return

        result = latest_version > get_installed_version()
        if result:
            click.echo(
                f"""An update to CumulusCI is available. To install the update, run this command: {get_cci_upgrade_command()}""",
                err=True,
            )

        if sys.version_info < LOWEST_SUPPORTED_VERSION:
            click.echo(
                "Sorry! Your Python version is not supported. Please upgrade to Python 3.9.",
                err=True,
            )


def get_installed_version():
    """returns the version name (e.g. 2.0.0b58) that is installed"""
    return pkg_resources.parse_version(__version__)


def win32_long_paths_enabled() -> bool:
    """Boolean indicating whether long paths are available on Windows systems.

    Reads the Windows Registry the running platform. Throws ModuleNotFoundError
    if run on non-Windows platforms.
    """
    # Only present on windows, so import it here instead
    import winreg

    access_registry = winreg.ConnectRegistry(None, winreg.HKEY_LOCAL_MACHINE)
    access_key = winreg.OpenKey(
        access_registry, r"SYSTEM\CurrentControlSet\Control\FileSystem"
    )

    is_enabled, _ = winreg.QueryValueEx(access_key, "LongPathsEnabled")

    return is_enabled == 1


def warn_if_no_long_paths(console: Console = Console()) -> None:
    """Print a warning to the user if long paths are not enabled."""
    if sys.platform.startswith("win") and not win32_long_paths_enabled():
        console.print(WIN_LONG_PATH_WARNING)
