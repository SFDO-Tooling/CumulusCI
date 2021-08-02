import code
import contextlib
import pdb
import runpy
import sys
import traceback

import click
import requests

import cumulusci
from cumulusci.core.debug import set_debug_mode
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.logging import tee_stdout_stderr

from .error import error
from .flow import flow
from .logger import get_tempfile_logger, init_logger
from .org import org
from .project import project
from .runtime import CliRuntime, pass_runtime
from .service import service
from .task import task
from .utils import check_latest_version, get_installed_version, get_latest_final_version

SUGGEST_ERROR_COMMAND = (
    """Run this command for more information about debugging errors: cci error --help"""
)

USAGE_ERRORS = (CumulusCIUsageError, click.UsageError)


#
# Root command
#
def main(args=None):
    """Main CumulusCI CLI entry point.

    This runs as the first step in processing any CLI command.

    This wraps the `click` library in order to do some initialization and centralized error handling.
    """
    with contextlib.ExitStack() as stack:
        args = args or sys.argv
        # Check for updates _unless_ we've been asked to output JSON,
        # or if we're going to check anyway as part of the `version` command.
        is_version_command = len(args) > 1 and args[1] == "version"
        if "--json" not in args and not is_version_command:
            check_latest_version()

        # Only create logfiles for commands that are not `cci error`
        is_error_command = len(args) > 2 and args[1] == "error"
        tempfile_path = None
        if not is_error_command:
            logger, tempfile_path = get_tempfile_logger()
            stack.enter_context(tee_stdout_stderr(args, logger, tempfile_path))

        debug = "--debug" in args
        if debug:
            args.remove("--debug")

        with set_debug_mode(debug):
            try:
                runtime = CliRuntime(load_keychain=False)
            except Exception as e:
                handle_exception(e, is_error_command, tempfile_path, debug)
                sys.exit(1)

            runtime.check_cumulusci_version()
            should_show_stacktraces = runtime.universal_config.cli__show_stacktraces

            init_logger(log_requests=debug)
            # Hand CLI processing over to click, but handle exceptions
            try:
                cli(args[1:], standalone_mode=False, obj=runtime)
            except click.Abort:  # Keyboard interrupt
                show_debug_info() if debug else click.echo("\nAborted!", err=True)
                sys.exit(1)
            except Exception as e:
                if debug:
                    show_debug_info()
                else:
                    handle_exception(
                        e, is_error_command, tempfile_path, should_show_stacktraces
                    )
                sys.exit(1)


def handle_exception(error, is_error_cmd, logfile_path, should_show_stacktraces=False):
    """Displays error of appropriate message back to user, prompts user to investigate further
    with `cci error` commands, and writes the traceback to the latest logfile.
    """
    if isinstance(error, requests.exceptions.ConnectionError):
        connection_error_message()
    elif isinstance(error, click.ClickException):
        click.echo(click.style(f"Error: {error.format_message()}", fg="red"), err=True)
    else:
        click.echo(click.style(f"{error}", fg="red"), err=True)
    # Only suggest gist command if it wasn't run
    if not is_error_cmd:
        click.echo(click.style(SUGGEST_ERROR_COMMAND, fg="yellow"), err=True)

    # This is None if we're handling an exception for a `cci error` command.
    if logfile_path:
        with open(logfile_path, "a") as log_file:
            traceback.print_exc(file=log_file)  # log stacktrace silently

    if should_show_stacktraces and not isinstance(error, USAGE_ERRORS):
        raise error


def connection_error_message():
    message = (
        "We encountered an error with your internet connection. "
        "Please check your connection and try the last cci command again."
    )
    click.echo(click.style(message, fg="red"), err=True)


def show_debug_info():
    """Displays the traceback and opens pdb"""
    traceback.print_exc()
    pdb.post_mortem()


@click.group("main", help="")
def cli():
    """Top-level `click` command group."""


@cli.command(name="version", help="Print the current version of CumulusCI")
def version():
    click.echo("CumulusCI version: ", nl=False)
    click.echo(click.style(cumulusci.__version__, bold=True), nl=False)
    click.echo(f" ({sys.argv[0]})")
    click.echo(f"Python version: {sys.version.split()[0]}", nl=False)
    click.echo(f" ({sys.executable})")

    click.echo()
    current_version = get_installed_version()
    latest_version = get_latest_final_version()
    if latest_version > current_version:
        click.echo(
            f"There is a newer version of CumulusCI available ({str(latest_version)})."
        )
        click.echo(f"To upgrade, run `{get_cci_upgrade_command()}`")
        click.echo(
            f"Release notes: https://github.com/SFDO-Tooling/CumulusCI/releases/tag/v{str(latest_version)}"
        )
    else:
        click.echo("You have the latest version of CumulusCI.")

    click.echo()


@cli.command(name="shell", help="Drop into a Python shell")
@click.option("--script", help="Path to a script to run", type=click.Path())
@click.option("--python", help="Python code to run directly")
@pass_runtime(require_project=False, require_keychain=True)
def shell(runtime, script=None, python=None):
    # alias for backwards-compatibility
    variables = {
        "config": runtime,
        "runtime": runtime,
        "project_config": runtime.project_config,
    }

    if script:
        if python:
            raise click.UsageError("Cannot specify both --script and --python")
        runpy.run_path(script, init_globals=variables)
    elif python:
        exec(python, variables)
    else:
        code.interact(local=variables)


# Top Level Groups

cli.add_command(error)
cli.add_command(project)
cli.add_command(org)
cli.add_command(service)
cli.add_command(task)
cli.add_command(flow)
