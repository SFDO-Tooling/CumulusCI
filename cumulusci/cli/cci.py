import code
import contextlib
import hashlib
import os
import pdb
import platform
import runpy
import sys
import traceback

import click
import requests
import rich
import sentry_sdk
from rich.console import Console
from rich.markup import escape

import cumulusci
from cumulusci.core.debug import set_debug_mode
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.http.requests_utils import init_requests_trust
from cumulusci.utils.logging import tee_stdout_stderr

from .error import error
from .flow import flow
from .logger import get_tempfile_logger, init_logger
from .org import org
from .plan import plan
from .plugin import plugin
from .project import project
from .robot import robot
from .runtime import CliRuntime, pass_runtime
from .service import service
from .task import task
from .utils import (
    check_latest_version,
    get_installed_version,
    get_latest_final_version,
    warn_if_no_long_paths,
)

SENTRY_DSN = "https://774d755112e0f997c8d6650052dc057b@o98429.ingest.us.sentry.io/4510699827691520"


def _get_sentry_environment():
    """Determine Sentry environment based on version or env var.

    Returns 'development' for dev/local builds, 'production' for releases.
    Can be overridden with CCI_ENVIRONMENT env var.
    """
    if env := os.environ.get("CCI_ENVIRONMENT"):
        return env

    version = cumulusci.__version__
    # Dev versions contain 'dev', 'alpha', 'beta', 'rc', or 'unknown'
    if any(tag in version.lower() for tag in ("dev", "alpha", "beta", "rc", "unknown")):
        return "development"
    return "production"


def _get_anonymous_user_id():
    """Generate an anonymous user ID based on machine identifier.

    Uses a hash of stable machine identifiers to create a unique
    but non-identifiable user ID for error grouping.
    """
    # Combine stable system identifiers for consistent hashing
    # platform.node() = hostname, platform.machine() = arch,
    # platform.processor() = processor info
    machine_id = f"{platform.node()}-{platform.machine()}-{platform.processor()}"
    return hashlib.sha256(machine_id.encode()).hexdigest()[:16]


def _detect_ci_environment():
    """Detect which CI environment CumulusCI is running in, if any."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        return "github_actions"
    elif os.environ.get("CIRCLECI"):
        return "circleci"
    elif os.environ.get("GITLAB_CI"):
        return "gitlab"
    elif os.environ.get("JENKINS_URL") or os.environ.get("JENKINS_HOME"):
        return "jenkins"
    elif os.environ.get("BITBUCKET_PIPELINES"):
        return "bitbucket"
    elif os.environ.get("TF_BUILD"):
        return "azure_devops"
    elif os.environ.get("CI"):
        return "unknown_ci"
    return None


def _set_sentry_user_context():
    """Set anonymized user context for Sentry.

    Sets anonymous user ID and OS/device context using Sentry's recognized structure.
    No PII is collected.
    """
    sentry_sdk.set_user({"id": _get_anonymous_user_id()})

    # Use Sentry's recognized OS context structure
    sentry_sdk.set_context(
        "os",
        {
            "name": platform.system(),
            "version": platform.release(),
            "build": platform.version(),
        },
    )

    # Use Sentry's recognized device context for architecture
    sentry_sdk.set_context(
        "device",
        {
            "arch": platform.machine(),
        },
    )

    # CI environment detection
    if ci_env := _detect_ci_environment():
        sentry_sdk.set_tag("ci", ci_env)


def init_sentry():
    """Initialize Sentry error tracking.

    Telemetry is OFF by default. To enable, set CCI_ENABLE_TELEMETRY=1 in environment.
    You can also override the DSN with SENTRY_DSN or environment with CCI_ENVIRONMENT.
    """
    if os.environ.get("CCI_ENABLE_TELEMETRY", "").lower() not in ("1", "true", "yes"):
        return

    dsn = os.environ.get("SENTRY_DSN", SENTRY_DSN)
    if not dsn:
        return

    try:
        sentry_sdk.init(
            dsn=dsn,
            release=cumulusci.__version__,
            environment=_get_sentry_environment(),
            send_default_pii=False,
            attach_stacktrace=True,
            max_breadcrumbs=50,
        )
    except Exception as e:
        # Invalid DSN or other init error - disable telemetry gracefully
        # Don't crash the CLI just because telemetry configuration is wrong
        import sys

        print(
            f"Warning: Failed to initialize telemetry: {e}. Telemetry disabled.",
            file=sys.stderr,
        )
        return

    _set_sentry_user_context()


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
    # Initialize Sentry early to capture any errors during startup
    init_sentry()

    with contextlib.ExitStack() as stack:
        args = args or sys.argv

        # (If enabled) set up requests to validate certs using system CA certs instead of certifi
        init_requests_trust()

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
                # Capture to Sentry (for non-usage errors)
                if not isinstance(e, USAGE_ERRORS):
                    sentry_sdk.capture_exception(e)
                handle_exception(e, is_error_command, tempfile_path, debug)
                sys.exit(1)

            runtime.check_cumulusci_version()
            should_show_stacktraces = runtime.universal_config.cli__show_stacktraces

            init_logger(debug=debug)
            # Hand CLI processing over to click, but handle exceptions
            try:
                cli(args[1:], standalone_mode=False, obj=runtime)
            except click.Abort:  # Keyboard interrupt
                console = Console()
                show_debug_info() if debug else console.print("\n[red bold]Aborted!")
                sys.exit(1)
            except Exception as e:
                # Capture to Sentry regardless of debug mode (for non-usage errors)
                if not isinstance(e, USAGE_ERRORS):
                    sentry_sdk.capture_exception(e)

                if debug:
                    show_debug_info()
                else:
                    handle_exception(
                        e,
                        is_error_command,
                        tempfile_path,
                        should_show_stacktraces,
                    )
                sys.exit(1)


def handle_exception(
    error,
    is_error_cmd,
    logfile_path,
    should_show_stacktraces=False,
):
    """Displays error of appropriate message back to user, prompts user to investigate further
    with `cci error` commands, and writes the traceback to the latest logfile.
    """
    error_console = Console(stderr=True)
    if isinstance(error, requests.exceptions.ConnectionError):
        connection_error_message(error_console)
    elif isinstance(error, click.ClickException):
        error_console.print(f"[red bold]Error: {escape(error.format_message())}")
    else:
        # We call str ourselves to make Typeguard shut up.
        error_console.print(f"[red bold]Error: {escape(str(error))}")
    # Only suggest gist command if it wasn't run
    if not is_error_cmd:
        error_console.print(f"[yellow]{SUGGEST_ERROR_COMMAND}")

    # This is None if we're handling an exception for a `cci error` command.
    if logfile_path:
        with open(logfile_path, "a") as log_file:
            traceback.print_exc(file=log_file)  # log stacktrace silently

    if should_show_stacktraces and not isinstance(error, USAGE_ERRORS):
        error_console.print_exception()


def connection_error_message(console: Console):
    message = (
        "We encountered an error with your internet connection. "
        "Please check your connection and try the last cci command again."
    )
    console.print(f"[red bold]{message}")


def show_debug_info():
    """Displays the traceback and opens pdb"""
    traceback.print_exc()
    pdb.post_mortem()


def show_version_info():
    console = rich.get_console()
    console.print(f"CumulusCI version: {cumulusci.__version__} ({sys.argv[0]})")
    console.print(f"Python version: {sys.version.split()[0]} ({sys.executable})")
    console.print()
    warn_if_no_long_paths(console=console)

    current_version = get_installed_version()
    latest_version = get_latest_final_version()

    if not latest_version > current_version:
        console.print("You have the latest version of CumulusCI :sun_behind_cloud:\n")
        display_release_notes_link(str(latest_version))
        return

    console.print(
        f"[yellow]There is a newer version of CumulusCI available: {str(latest_version)}"
    )
    console.print(f"To upgrade, run `{get_cci_upgrade_command()}`")
    display_release_notes_link(str(latest_version))


def display_release_notes_link(latest_version: str) -> None:
    """Provide a link to the latest CumulusCI Release Notes"""
    release_notes_link = (
        f"https://github.com/SFDO-Tooling/CumulusCI/releases/tag/v{latest_version}"
    )
    console = rich.get_console()
    console.print(
        f"See the latest CumulusCI Release Notes: [link={release_notes_link}]{release_notes_link}[/link]"
    )


def version_info_wrapper(
    ctx: click.Context, param: click.Parameter, value: bool
) -> None:
    if not value:
        return
    show_version_info()
    ctx.exit()


@click.group("main", help="")
@click.option(  # based on https://click.palletsprojects.com/en/8.1.x/options/#callbacks-and-eager-options
    "--version",
    is_flag=True,
    expose_value=False,
    is_eager=True,
    help="Show the version and exit.",
    callback=version_info_wrapper,
)
def cli():
    """Top-level `click` command group."""


@cli.command(name="version", help="Print the current version of CumulusCI")
def version():
    show_version_info()


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


@cli.command(
    name="telemetry", help="Show telemetry status and what data would be collected"
)
def telemetry():
    """Display telemetry configuration and data that would be collected."""
    console = rich.get_console()

    # Check if telemetry is enabled
    telemetry_enabled = os.environ.get("CCI_ENABLE_TELEMETRY", "").lower() in (
        "1",
        "true",
        "yes",
    )

    console.print()
    if telemetry_enabled:
        console.print("[green bold]Telemetry is ENABLED[/green bold]")
    else:
        console.print("[yellow bold]Telemetry is DISABLED (default)[/yellow bold]")
        console.print(
            "To enable telemetry, set: [cyan]export CCI_ENABLE_TELEMETRY=1[/cyan]"
        )

    console.print()
    console.print("[bold]Data that would be collected:[/bold]")
    console.print()

    # Show what would be collected
    console.print(f"  [dim]CumulusCI Version:[/dim] {cumulusci.__version__}")
    console.print(f"  [dim]Environment:[/dim] {_get_sentry_environment()}")
    console.print(f"  [dim]Anonymous User ID:[/dim] {_get_anonymous_user_id()}")
    console.print()
    console.print("  [dim]OS Context:[/dim]")
    console.print(f"    [dim]Name:[/dim] {platform.system()}")
    console.print(f"    [dim]Version:[/dim] {platform.release()}")
    console.print(f"    [dim]Build:[/dim] {platform.version()}")
    console.print()
    console.print("  [dim]Device Context:[/dim]")
    console.print(f"    [dim]Architecture:[/dim] {platform.machine()}")

    ci_env = _detect_ci_environment()
    if ci_env:
        console.print()
        console.print(f"  [dim]CI Environment:[/dim] {ci_env}")

    console.print()
    console.print("[bold]Data NOT collected:[/bold]")
    console.print("  - Salesforce credentials or tokens")
    console.print("  - Org data or metadata")
    console.print("  - Project-specific configuration")
    console.print("  - File contents or paths")
    console.print("  - Personal information")
    console.print()
    console.print(
        "For more information, see: "
        "[link=https://claritisoftware.github.io/CumulusCI/env-var-reference.html#telemetry]"
        "https://claritisoftware.github.io/CumulusCI/env-var-reference.html#telemetry[/link]"
    )


# Top Level Groups

cli.add_command(error)
cli.add_command(project)
cli.add_command(org)
cli.add_command(service)
cli.add_command(task)
cli.add_command(flow)
cli.add_command(plan)
cli.add_command(plugin)
cli.add_command(robot)
