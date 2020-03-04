import io
import logging
import platform
import sarge
import sys

logger = logging.getLogger(__name__)


def sfdx(
    command,
    username=None,
    log_note=None,
    access_token=None,
    args=None,
    env=None,
    capture_output=True,
    check_return=False,
):
    """Call an sfdx command and capture its output.

    Be sure to quote user input that is part of the command using `shell_quote`.

    Returns a `sarge` Command instance with returncode, stdout, stderr
    """
    command = "sfdx {}".format(command)
    if args is not None:
        for arg in args:
            command += " " + shell_quote(arg)
    if username:
        command += f" -u {shell_quote(username)}"
    if log_note:
        logger.info("{} with command: {}".format(log_note, command))
    # Avoid logging access token
    if access_token:
        command += f" -u {shell_quote(access_token)}"
    p = sarge.Command(
        command,
        stdout=sarge.Capture(buffer_size=-1) if capture_output else None,
        stderr=sarge.Capture(buffer_size=-1) if capture_output else None,
        shell=True,
        env=env,
    )
    p.run()
    if capture_output or (check_return and p.returncode):
        p.stdout_text = io.TextIOWrapper(p.stdout, encoding=sys.stdout.encoding)
        p.stderr_text = io.TextIOWrapper(p.stderr, encoding=sys.stdout.encoding)
    if check_return and p.returncode:
        raise Exception(
            f"Command exited with return code {p.returncode}:\n{p.stderr_text.read()}"
        )
    return p


def shell_quote(s):
    if platform.system() == "Windows":
        assert isinstance(s, str)
        if not s:
            result = '""'
        elif '"' not in s:
            result = s
        else:
            escaped = s.replace('"', r"\"")
            result = f'"{escaped}"'
        return result
    else:
        return sarge.shell_quote(s)
