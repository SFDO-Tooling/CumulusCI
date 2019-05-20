import logging
import sarge

logger = logging.getLogger(__name__)


def sfdx(command, username=None, log_note=None):
    """Call an sfdx command and capture its output.

    Be sure to quote user input that is part of the command using `sarge.shell_format`.

    Returns a `sarge` Command instance with returncode, stdout, stderr
    """
    command = "sfdx {}".format(command)
    if username:
        command += sarge.shell_format(" -u {0}", username)
    if log_note:
        logger.info("{} with command: {}".format(log_note, command))
    p = sarge.Command(
        command,
        stdout=sarge.Capture(buffer_size=-1),
        stderr=sarge.Capture(buffer_size=-1),
        shell=True,
    )
    p.run()
    return p
