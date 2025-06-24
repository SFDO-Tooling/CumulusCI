import contextlib
import io
import json
import logging
import os
import pathlib
import platform
import sys
import typing as T
from os import PathLike
from zipfile import ZipFile

import sarge

# Fix for TextIOWrapper flush issue with sarge.Capture objects
# Add flush method to sarge.Capture to prevent AttributeError during garbage collection
if not hasattr(sarge.Capture, 'flush'):
    def _capture_flush(self):
        """No-op flush method for sarge.Capture compatibility with TextIOWrapper"""
        pass
    sarge.Capture.flush = _capture_flush

from cumulusci.core.enums import StrEnum
from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.utils import temporary_dir

logger = logging.getLogger(__name__)


def sfdx(
    command,
    username=None,
    log_note=None,
    access_token=None,
    args: T.Optional[T.List[str]] = None,
    env=None,
    capture_output=True,
    check_return=False,
):
    """Call an sfdx command and capture its output.

    Be sure to quote user input that is part of the command using `shell_quote`.

    Returns a `sarge` Command instance with returncode, stdout, stderr
    """
    command = f"sf {command}"
    if args is not None:
        for arg in args:
            command += " " + shell_quote(arg)
    if username:
        command += f" -o {shell_quote(username)}"
    if log_note:
        logger.info(f"{log_note} with command: {command}")
    # Avoid logging access token
    if access_token:
        command += f" -o {shell_quote(access_token)}"
    env = env or {}
    p = sarge.Command(
        command,
        stdout=sarge.Capture(buffer_size=-1) if capture_output else None,
        stderr=sarge.Capture(buffer_size=-1) if capture_output else None,
        shell=True,
        env={**env, "SFDX_TOOL": "CCI"},
    )
    p.run()
    if capture_output:
        p.stdout_text = io.TextIOWrapper(p.stdout, encoding=sys.stdout.encoding)
        p.stderr_text = io.TextIOWrapper(p.stderr, encoding=sys.stdout.encoding)
    if check_return and p.returncode:
        message = f"Command exited with return code {p.returncode}"
        if capture_output:
            message += f":\n{p.stderr_text.read()}"
        raise Exception(message)
    return p


def shell_quote(s: str):
    if platform.system() == "Windows":
        assert isinstance(s, str)
        if not s:
            result = '""'
        elif '"' not in s:
            result = s
            if " " in result:
                result = f'"{result}"'
        else:
            escaped = s.replace('"', r"\"")
            result = f'"{escaped}"'

        return result
    else:
        return sarge.shell_quote(s)


def get_default_devhub_username():
    p = sfdx(
        "config get target-dev-hub --json",
        log_note="Getting default Dev Hub username from sfdx",
        check_return=True,
    )
    result = json.load(p.stdout_text)
    if "result" not in result or "value" not in result["result"][0]:
        raise SfdxOrgException(
            "No sf config found for target-dev-hub. "
            "Please use the sf config set to set the target-dev-hub and run again."
        )
    username = result["result"][0]["value"]
    return username


class SourceFormat(StrEnum):
    SFDX = "SFDX"
    MDAPI = "MDAPI"


def get_source_format_for_path(path: T.Optional[PathLike]) -> SourceFormat:
    if pathlib.Path(path or pathlib.Path.cwd(), "package.xml").exists():
        return SourceFormat.MDAPI

    return SourceFormat.SFDX


def get_source_format_for_zipfile(
    zf: ZipFile, subfolder: T.Optional[str]
) -> SourceFormat:
    namelist = zf.namelist()

    target_name = str(pathlib.PurePosixPath(subfolder or "", "package.xml"))

    if target_name in namelist:
        return SourceFormat.MDAPI

    return SourceFormat.SFDX


@contextlib.contextmanager
def convert_sfdx_source(
    path: T.Optional[PathLike], name: T.Optional[str], logger: logging.Logger
):
    mdapi_path = None
    with contextlib.ExitStack() as stack:
        # Convert SFDX -> MDAPI format if path exists but does not have package.xml
        if (
            len(os.listdir(path))  # path is None -> CWD
            and get_source_format_for_path(path) is SourceFormat.SFDX
        ):
            logger.info("Converting from SFDX to MDAPI format.")
            mdapi_path = stack.enter_context(temporary_dir(chdir=False))
            args = ["-d", mdapi_path]
            if path:
                # No path means convert default package directory in the CWD
                args += ["-r", str(path)]
            if name:
                args += ["-n", name]
            sfdx(
                "project convert source",
                args=args,
                capture_output=True,
                check_return=True,
            )

        yield mdapi_path or path
