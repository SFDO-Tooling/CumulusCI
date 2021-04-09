from collections import defaultdict

import code
import json
import re
import os
import pdb
import sys
import time
import traceback
import runpy
import contextlib
from datetime import datetime
from pathlib import Path

import click
import pkg_resources
import requests

import cumulusci
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.exceptions import (
    CumulusCIUsageError,
    ServiceNotConfigured,
    FlowNotFoundError,
)
from cumulusci.utils.http.requests_utils import safe_json_from_response
from cumulusci.core.debug import set_debug_mode


from cumulusci.core.utils import import_global, format_duration
from cumulusci.cli.utils import group_items
from cumulusci.cli.runtime import CliRuntime
from cumulusci.cli.runtime import get_installed_version
from cumulusci.cli.ui import CliTable
from cumulusci.utils import document_flow, flow_ref_title_and_intro
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.logging import tee_stdout_stderr
from cumulusci.utils.yaml.cumulusci_yml import cci_safe_load

from .logger import init_logger, get_tempfile_logger
from .runtime import pass_runtime

from .error import error
from .org import org
from .project import project
from .task import task


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
    """ return the latest version of cumulusci in pypi, be defensive """
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
    """ checks for the latest version of cumulusci from pypi, max once per hour """
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


@cli.group("flow", help="Commands for finding and running flows for a project")
def flow():
    pass


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
    configured_services = runtime.keychain.list_services()
    plain = plain or runtime.universal_config.cli__plain_output

    data = [["Name", "Description", "Configured"]]
    for serv, schema in services.items():
        schema["configured"] = serv in configured_services
        data.append([serv, schema["description"], schema["configured"]])

    if print_json:
        click.echo(json.dumps(services))
        return None

    rows_to_dim = [row_index for row_index, row in enumerate(data) if not row[2]]
    table = CliTable(
        data,
        title="Services",
        wrap_cols=["Description"],
        bool_cols=["Configured"],
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

    def get_command(self, ctx, name):
        runtime = ctx.obj
        runtime._load_keychain()
        services = self._get_services_config(runtime)
        try:
            service_config = services[name]
        except KeyError:
            raise click.UsageError(f"Sorry, I don't know about the '{name}' service.")
        attributes = service_config["attributes"].items()

        params = [self._build_param(attr, cnfg) for attr, cnfg in attributes]
        if runtime.project_config is not None:
            params.append(click.Option(("--project",), is_flag=True))

        def callback(*args, **kwargs):
            if runtime.project_config is None:
                project = False
            else:
                project = kwargs.pop("project", False)
            serv_conf = dict(
                (k, v) for k, v in list(kwargs.items()) if v is not None
            )  # remove None values

            # A service can define a callable to validate the service config
            validator_path = service_config.get("validator")
            if validator_path:
                validator = import_global(validator_path)
                validator(serv_conf)

            runtime.keychain.set_service(name, ServiceConfig(serv_conf), project)
            if project:
                click.echo(f"{name} is now configured for this project.")
            else:
                click.echo(f"{name} is now configured for all CumulusCI projects.")

        ret = click.Command(name, params=params, callback=callback)
        return ret


@service.command(
    cls=ConnectServiceCommand, name="connect", help="Connect a CumulusCI task service"
)
def service_connect():
    pass


@service.command(name="info", help="Show the details of a connected service")
@click.argument("service_name")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@pass_runtime(require_project=False, require_keychain=True)
def service_info(runtime, service_name, plain):
    try:
        plain = plain or runtime.universal_config.cli__plain_output
        service_config = runtime.keychain.get_service(service_name)
        service_data = [["Key", "Value"]]
        service_data.extend(
            [
                [click.style(k, bold=True), str(v)]
                for k, v in service_config.config.items()
            ]
        )
        wrap_cols = ["Value"] if not plain else None
        service_table = CliTable(service_data, title=service_name, wrap_cols=wrap_cols)
        service_table._table.inner_heading_row_border = False
        service_table.echo(plain)
    except ServiceNotConfigured:
        click.echo(
            "{0} is not configured for this project.  Use service connect {0} to configure.".format(
                service_name
            )
        )


@flow.command(name="doc", help="Exports RST format documentation for all flows")
@pass_runtime(require_project=False)
def flow_doc(runtime):
    flow_info_path = Path(__file__, "..", "..", "..", "docs", "flows.yml").resolve()
    with open(flow_info_path, "r", encoding="utf-8") as f:
        flow_info = cci_safe_load(f)
    click.echo(flow_ref_title_and_intro(flow_info["intro_blurb"]))
    flow_info_groups = list(flow_info["groups"].keys())

    flows = runtime.get_available_flows()
    flows_by_group = group_items(flows)
    flow_groups = sorted(
        flows_by_group.keys(),
        key=lambda group: flow_info_groups.index(group)
        if group in flow_info_groups
        else 100,
    )

    for group in flow_groups:
        click.echo(f"{group}\n{'-' * len(group)}")
        if group in flow_info["groups"]:
            click.echo(flow_info["groups"][group]["description"])

        for flow in sorted(flows_by_group[group]):
            flow_name, flow_description = flow
            try:
                flow_coordinator = runtime.get_flow(flow_name)
            except FlowNotFoundError as e:
                raise click.UsageError(str(e))

            additional_info = None
            if flow_name in flow_info.get("flows", {}):
                additional_info = flow_info["flows"][flow_name]["rst_text"]

            click.echo(
                document_flow(
                    flow_name,
                    flow_description,
                    flow_coordinator,
                    additional_info=additional_info,
                )
            )
            click.echo("")


@flow.command(name="list", help="List available flows for the current context")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=False)
def flow_list(runtime, plain, print_json):
    plain = plain or runtime.universal_config.cli__plain_output
    flows = runtime.get_available_flows()
    if print_json:
        click.echo(json.dumps(flows))
        return None

    flow_groups = group_items(flows)
    for group, flows in flow_groups.items():
        data = [["Flow", "Description"]]
        data.extend(sorted(flows))
        table = CliTable(data, group, wrap_cols=["Description"])
        table.echo(plain)

    click.echo(
        "Use "
        + click.style("cci flow info <flow_name>", bold=True)
        + " to get more information about a flow."
    )


@flow.command(name="info", help="Displays information for a flow")
@click.argument("flow_name")
@pass_runtime(require_keychain=True)
def flow_info(runtime, flow_name):
    try:
        coordinator = runtime.get_flow(flow_name)
        output = coordinator.get_summary()
        click.echo(output)
    except FlowNotFoundError as e:
        raise click.UsageError(str(e))


@flow.command(name="run", help="Runs a flow")
@click.argument("flow_name")
@click.option(
    "--org",
    help="Specify the target org.  By default, runs against the current default org",
)
@click.option(
    "--delete-org",
    is_flag=True,
    help="If set, deletes the scratch org after the flow completes",
)
@click.option(
    "--debug", is_flag=True, help="Drops into pdb, the Python debugger, on an exception"
)
@click.option(
    "-o",
    nargs=2,
    multiple=True,
    help="Pass task specific options for the task as '-o taskname__option value'.  You can specify more than one option by using -o more than once.",
)
@click.option(
    "--skip",
    multiple=True,
    help="Specify task names that should be skipped in the flow.  Specify multiple by repeating the --skip option",
)
@click.option(
    "--no-prompt",
    is_flag=True,
    help="Disables all prompts.  Set for non-interactive mode use such as calling from scripts or CI systems",
)
@pass_runtime(require_keychain=True)
def flow_run(runtime, flow_name, org, delete_org, debug, o, skip, no_prompt):

    # Get necessary configs
    org, org_config = runtime.get_org(org)
    if delete_org and not org_config.scratch:
        raise click.UsageError("--delete-org can only be used with a scratch org")

    # Parse command line options
    options = defaultdict(dict)
    if o:
        for key, value in o:
            if "__" in key:
                task_name, option_name = key.split("__")
                options[task_name][option_name] = value
            else:
                raise click.UsageError(
                    "-o option for flows should contain __ to split task name from option name."
                )

    # Create the flow and handle initialization exceptions
    try:
        coordinator = runtime.get_flow(flow_name, options=options)
        start_time = datetime.now()
        coordinator.run(org_config)
        duration = datetime.now() - start_time
        click.echo(f"Ran {flow_name} in {format_duration(duration)}")

    finally:
        runtime.alert(f"Flow Complete: {flow_name}")

    # Delete the scratch org if --delete-org was set
    if delete_org:
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo(
                "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
            )
            click.echo(str(e))
