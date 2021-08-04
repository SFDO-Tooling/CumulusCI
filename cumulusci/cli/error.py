import platform
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

import click
import github3

import cumulusci
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.github import check_github_scopes, create_gist, get_github_api

from .runtime import pass_runtime

GIST_404_ERR_MSG = """A 404 error code was returned when trying to create your gist.
Please ensure that your GitHub personal access token has the 'Create gists' scope."""


@click.group("error", short_help="Get or share information about an error")
def error():
    """
    Get or share information about an error

    If you'd like to dig into an error more yourself,
    you can get the last few lines of context about it
    from `cci error info`.

    If you'd like to submit it to a developer for conversation,
    you can use the `cci error gist` command. Just make sure
    that your GitHub access token has the 'create gist' scope.

    If you'd like to regularly see stack traces, set the `show_stacktraces`
    option to `True` in the "cli" section of `~/.cumulusci/cumulusci.yml`, or to
    see a stack-trace (and other debugging information) just once, use the `--debug`
    command line option.

    For more information on working with errors in CumulusCI visit:
    https://cumulusci.readthedocs.io/en/latest/features.html#working-with-errors
    """


CCI_LOGFILE_PATH = Path.home() / ".cumulusci" / "logs" / "cci.log"


@error.command(
    name="info",
    help="Outputs the most recent traceback (if one exists in the most recent log)",
)
@click.option("--max-lines", "-m", type=int)
def error_info(max_lines: int = 0):
    if not CCI_LOGFILE_PATH.is_file():
        click.echo(f"No logfile found at: {CCI_LOGFILE_PATH}")
    else:
        output = lines_from_traceback(
            CCI_LOGFILE_PATH.read_text(encoding="utf-8"), max_lines
        )
        click.echo(output)


def lines_from_traceback(log_content: str, max_lines: int = 0) -> str:
    """Returns the the last max_lines of the logfile,
    or the whole traceback, whichever is shorter. If
    no stacktrace is found in the logfile, the user is
    notified.
    """
    stacktrace_start = "Traceback (most recent call last):"
    if stacktrace_start not in log_content:
        return f"\nNo stacktrace found in: {CCI_LOGFILE_PATH}\n"

    stacktrace = ""
    for i, line in enumerate(reversed(log_content.split("\n")), 1):
        stacktrace = "\n" + line + stacktrace
        if stacktrace_start in line:
            break
        if i == max_lines:
            break

    return stacktrace


@error.command(name="gist", help="Creates a GitHub gist from the latest logfile")
@pass_runtime(require_project=False, require_keychain=True)
def gist(runtime):
    if CCI_LOGFILE_PATH.is_file():
        log_content = CCI_LOGFILE_PATH.read_text(encoding="utf-8")
    else:
        log_not_found_msg = """No logfile to open at path: {}
        Please ensure you're running this command from the same directory you were experiencing an issue."""
        error_msg = log_not_found_msg.format(CCI_LOGFILE_PATH)
        click.echo(error_msg)
        raise CumulusCIException(error_msg)

    last_cmd_header = "\n\n\nLast Command Run\n================================\n"
    filename = f"cci_output_{datetime.utcnow()}.txt"
    files = {
        filename: {"content": f"{get_context_info()}{last_cmd_header}{log_content}"}
    }

    try:
        gh = runtime.keychain.get_service("github")
        gist = create_gist(
            get_github_api(gh.username, gh.password or gh.token),
            "CumulusCI Error Output",
            files,
        )
    except github3.exceptions.NotFoundError as exc:
        scope_warning = check_github_scopes(exc)
        raise CumulusCIException(GIST_404_ERR_MSG + f"\n\n{scope_warning}")
    except Exception as e:
        raise CumulusCIException(
            f"An error occurred attempting to create your gist:\n{e}"
        )
    else:
        click.echo(f"Gist created: {gist.html_url}")
        webbrowser.open(gist.html_url)


def get_context_info():
    host_info = platform.uname()

    info = []
    info.append(f"CumulusCI version: {cumulusci.__version__}")
    info.append(f"Python version: {sys.version.split()[0]} ({sys.executable})")
    info.append(f"Environment Info: {host_info.system} / {host_info.machine}")
    return "\n".join(info)
