from pathlib import Path
import code
import json
import pdb
import sys
import traceback
import runpy
import contextlib

import click
import requests

import cumulusci
from cumulusci.core.config import ServiceConfig
from cumulusci.core.debug import set_debug_mode
from cumulusci.core.exceptions import (
    CumulusCIUsageError,
    ServiceNotConfigured,
)
from cumulusci.core.utils import import_global
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.logging import tee_stdout_stderr

from .logger import init_logger, get_tempfile_logger
from .runtime import pass_runtime, CliRuntime
from .ui import CliTable
from .utils import get_installed_version, check_latest_version, get_latest_final_version

from .error import error
from .flow import flow
from .org import org
from .project import project
from .task import task


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
cli.add_command(task)
cli.add_command(flow)


@cli.group("service", help="Commands for connecting services to the keychain")
def service():
    pass


# Commands for group: service
@service.command(name="list", help="List services available for configuration and use")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=False, require_keychain=True)
def service_list(runtime, plain, print_json):
    services = (
        runtime.project_config.services
        if runtime.project_config is not None
        else runtime.universal_config.services
    )
    supported_service_types = list(services.keys())
    supported_service_types.sort()

    if print_json:
        click.echo(json.dumps(services))
        return None

    configured_services = runtime.keychain.list_services()
    plain = plain or runtime.universal_config.cli__plain_output

    data = [["Type", "Name", "Default", "Description"]]

    for service_type in supported_service_types:
        if service_type not in configured_services:
            data.append(
                [service_type, "", False, services[service_type]["description"]]
            )
            continue
        for alias in configured_services[service_type]:
            try:
                default_service_for_type = runtime.keychain._default_services[
                    service_type
                ]
            except KeyError:
                default_service_for_type = None
            data.append(
                [
                    service_type,
                    alias,
                    alias == default_service_for_type,
                    services[service_type]["description"],
                ]
            )

    rows_to_dim = [row_index for row_index, row in enumerate(data) if not row[1]]
    table = CliTable(
        data,
        title="Services",
        wrap_cols=["Description"],
        bool_cols=["Default"],
        dim_rows=rows_to_dim,
    )
    table.echo(plain)


class ConnectServiceCommand(click.MultiCommand):
    def _get_services_config(self, runtime):
        return (
            runtime.project_config.services
            if runtime.project_config
            else runtime.universal_config.services
        )

    def list_commands(self, ctx):
        """ list the services that can be configured """
        runtime = ctx.obj
        services = self._get_services_config(runtime)
        return sorted(services.keys())

    def _build_param(self, attribute, details):
        req = details["required"]
        return click.Option((f"--{attribute}",), prompt=req, required=req)

    def _get_default_options(self, runtime):
        options = []
        options.append(
            click.Option(
                ("--default",),
                is_flag=True,
                help="Set this service as the global defualt.",
            )
        )
        if runtime.project_config is not None:
            options.append(
                click.Option(
                    ("--project",),
                    is_flag=True,
                    help="Set this service as the default for this project only.",
                )
            )
        return options

    def get_command(self, ctx, service_type):
        runtime = ctx.obj
        runtime._load_keychain()
        services = self._get_services_config(runtime)

        try:
            service_config = services[service_type]
        except KeyError:
            raise click.UsageError(
                f"Sorry, I don't know about the '{service_type}' service."
            )

        attributes = service_config["attributes"].items()
        params = [self._build_param(attr, cnfg) for attr, cnfg in attributes]
        params.extend(self._get_default_options(runtime))

        def callback(*args, **kwargs):
            service_name = kwargs["service_name"]
            if service_name in runtime.keychain.list_services()[service_type]:
                click.confirm(
                    f"There is already a {service_type}:{service_name} service. Do you want to overwrite it?",
                    abort=True,
                )

            if runtime.project_config is None:
                set_project_default = False
            else:
                set_project_default = kwargs.pop("project", False)

            set_global_default = kwargs.pop("default", False)

            serv_conf = dict(
                (k, v) for k, v in list(kwargs.items()) if v is not None
            )  # remove None values

            # A service can define a callable to validate the service config
            validator_path = service_config.get("validator")
            if validator_path:
                validator = import_global(validator_path)
                validator(serv_conf)

            runtime.keychain.set_service(
                service_type,
                service_name,
                ServiceConfig(serv_conf),
            )
            click.echo(f"Service {service_type}:{service_name} is now connected")

            if set_global_default:
                runtime.keychain.set_default_service(
                    service_type, service_name, project=False
                )
                click.echo(
                    f"Service {service_type}:{service_name} is now the default for all CumulusCI projects"
                )
            if set_project_default:
                runtime.keychain.set_default_service(
                    service_type, service_name, project=True
                )
                project_name = runtime.project_config.project__name
                click.echo(
                    f"Service {service_type}:{service_name} is now the default for project '{project_name}'"
                )

        params.append(click.Argument(["service_name"]))
        return click.Command(service_type, params=params, callback=callback)


@service.command(
    cls=ConnectServiceCommand,
    name="connect",
    help="Connect an external service to CumulusCI",
)
def service_connect():
    pass


@service.command(name="info", help="Show the details of a connected service")
@click.argument("service_type")
@click.argument("service_name", required=False)
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@pass_runtime(require_project=False, require_keychain=True)
def service_info(runtime, service_type, service_name, plain):
    try:
        plain = plain or runtime.universal_config.cli__plain_output
        service_config = runtime.keychain.get_service(service_type, service_name)
        service_data = [["Key", "Value"]]
        service_data.extend(
            [
                [click.style(k, bold=True), str(v)]
                for k, v in service_config.config.items()
                if k != "service_name"
            ]
        )
        wrap_cols = ["Value"] if not plain else None
        service_table = CliTable(
            service_data, title=f"{service_type}/{service_name}", wrap_cols=wrap_cols
        )
        service_table._table.inner_heading_row_border = False
        service_table.echo(plain)
    except ServiceNotConfigured:
        click.echo(
            f"{service_type} is not configured for this project.  Use service connect {service_type} to configure."
        )


@service.command(
    name="default", help="Set the default service for a given service type."
)
@click.argument("service_type")
@click.argument("service_name")
@click.option(
    "--project",
    is_flag=True,
    help="Sets the service as the default for the current project.",
)
@pass_runtime(require_project=False, require_keychain=True)
def service_default(runtime, service_type, service_name, project):
    try:
        runtime.keychain.set_default_service(service_type, service_name, project)
    except ServiceNotConfigured as e:
        click.echo(f"An error occurred setting the default service: {e}")
        return
    if project:
        project_name = Path(runtime.keychain.project_local_dir).name
        click.echo(
            f"Service {service_type}:{service_name} is now the default for project '{project_name}'"
        )
    else:
        click.echo(
            f"Service {service_type}:{service_name} is now the default for all CumulusCI projects"
        )


@service.command(name="rename", help="Rename a service")
@click.argument("service_type")
@click.argument("current_name")
@click.argument("new_name")
@pass_runtime(require_project=False, require_keychain=True)
def service_rename(runtime, service_type, current_name, new_name):
    try:
        runtime.keychain.rename_service(service_type, current_name, new_name)
    except ServiceNotConfigured as e:
        click.echo(f"An error occurred renaming the service: {e}")
        return

    click.echo(f"Service {service_type}:{current_name} has been renamed to {new_name}")


@service.command(name="remove", help="Remove a service")
@click.argument("service_type")
@click.argument("service_name")
@pass_runtime(require_project=False, require_keychain=True)
def service_remove(runtime, service_type, service_name):
    new_default = None
    if (
        len(runtime.keychain.services[service_type].keys()) > 2
        and service_name == runtime.keychain._default_services[service_type]
    ):
        click.echo(
            f"The service you would like to remove is currently the default for {service_type} services."
        )
        click.echo("Your other services of the same type are:")
        for alias in runtime.keychain.list_services()[service_type]:
            if alias != service_name:
                click.echo(alias)
        new_default = click.prompt(
            "Enter the name of the service you would like as the new default"
        )
        if new_default not in runtime.keychain.list_services()[service_type]:
            click.echo(f"No service of type {service_type} with name: {new_default}")
            return

    try:
        runtime.keychain.remove_service(service_type, service_name)
        if new_default:
            runtime.keychain.set_default_service(service_type, new_default)
    except ServiceNotConfigured as e:
        click.echo(f"An error occurred removing the service: {e}")
        return

    click.echo(f"Service {service_type}:{service_name} has been removed.")
