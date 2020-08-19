from collections import defaultdict
from urllib.parse import urlparse

import code
import functools
import json
import re
import os
import platform
import pdb
import shutil
import sys
import time
import traceback
from datetime import datetime
import webbrowser
import contextlib
from pathlib import Path
import runpy

import click
import github3
import pkg_resources
import requests
from requests import exceptions
from rst2ansi import rst2ansi
from jinja2 import Environment
from jinja2 import PackageLoader

import cumulusci
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import UniversalConfig
from cumulusci.core.github import create_gist, get_github_api
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import FlowNotFoundError


from cumulusci.core.utils import import_global
from cumulusci.cli.runtime import CliRuntime
from cumulusci.cli.runtime import get_installed_version
from cumulusci.cli.ui import CliTable, CROSSMARK, SimpleSalesforceUIHelpers
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.utils import doc_task
from cumulusci.utils import parse_api_datetime
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils.git import current_branch
from cumulusci.utils.logging import tee_stdout_stderr
from cumulusci.oauth.salesforce import CaptureSalesforceOAuth

from .logger import init_logger, get_tempfile_logger


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
    res = requests.get("https://pypi.org/pypi/cumulusci/json", timeout=5).json()
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
            click.echo("Error checking cci version:")
            click.echo(str(e))
            return

        result = latest_version > get_installed_version()
        click.echo("Checking the version!")
        if result:
            click.echo(
                f"""An update to CumulusCI is available. To install the update, run this command: {get_cci_upgrade_command()}"""
            )


def render_recursive(data, indent=None):
    if indent is None:
        indent = 0
    indent_str = " " * indent
    if isinstance(data, list):
        for item in data:
            if isinstance(item, (bytes, str)):
                click.echo(f"{indent_str}- {item}")
            else:
                click.echo(f"{indent_str}-")
                render_recursive(item, indent=indent + 4)
    elif isinstance(data, dict):
        for key, value in data.items():
            key_str = click.style(str(key) + ":", bold=True)
            if isinstance(value, list):
                click.echo(f"{indent_str}{key_str}")
                render_recursive(value, indent=indent + 4)
            elif isinstance(value, dict):
                click.echo(f"{indent_str}{key_str}")
                render_recursive(value, indent=indent + 4)
            else:
                click.echo(f"{indent_str}{key_str} {value}")


# global reference to active runtime
RUNTIME = None


def pass_runtime(func=None, require_project=True, require_keychain=False):
    """Decorator which passes the CCI runtime object as the first arg to a click command."""

    def decorate(func):
        def new_func(*args, **kw):
            runtime = RUNTIME
            if require_project and runtime.project_config is None:
                raise runtime.project_config_error
            if require_keychain:
                runtime._load_keychain()
            func(RUNTIME, *args, **kw)

        return functools.update_wrapper(new_func, func)

    if func is None:
        return decorate
    else:
        return decorate(func)


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

        # Load CCI config
        global RUNTIME
        RUNTIME = CliRuntime(load_keychain=False)
        RUNTIME.check_cumulusci_version()

        # Configure logging
        debug = "--debug" in args
        if debug:
            args.remove("--debug")
        should_show_stacktraces = RUNTIME.universal_config.cli__show_stacktraces

        # Only create logfiles for commands
        # that are not `cci error`
        is_error_command = len(args) > 2 and args[1] == "error"
        tempfile_path = None
        if not is_error_command:
            logger, tempfile_path = get_tempfile_logger()
            stack.enter_context(tee_stdout_stderr(args, logger, tempfile_path))

        init_logger(log_requests=debug)
        # Hand CLI processing over to click, but handle exceptions
        try:
            cli(standalone_mode=False)
        except click.Abort:  # Keyboard interrupt
            show_debug_info() if debug else click.echo("\nAborted!")
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
    if isinstance(error, exceptions.ConnectionError):
        connection_error_message()
    elif isinstance(error, click.ClickException):
        click.echo(click.style(f"Error: {error.format_message()}", fg="red"))
    else:
        click.echo(click.style(f"Error: {error}", fg="red"))
    # Only suggest gist command if it wasn't run
    if not is_error_cmd:
        click.echo(click.style(SUGGEST_ERROR_COMMAND, fg="yellow"))

    # This is None if we're handling an exception for a
    # `cci error` command.
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
    click.echo(click.style(message, fg="red"))


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


GIST_404_ERR_MSG = """A 404 error code was returned when trying to create your gist.
Please ensure that your GitHub personal access token has the 'Create gists' scope."""


def get_context_info():
    host_info = platform.uname()

    info = []
    info.append(f"CumulusCI version: {cumulusci.__version__}")
    info.append(f"Python version: {sys.version.split()[0]} ({sys.executable})")
    info.append(f"Environment Info: {host_info.system} / {host_info.machine}")
    return "\n".join(info)


# Top Level Groups


@cli.group(
    "project", help="Commands for interacting with project repository configurations"
)
def project():
    pass


@cli.group("org", help="Commands for connecting and interacting with Salesforce orgs")
def org():
    pass


@cli.group("task", help="Commands for finding and running tasks for a project")
def task():
    pass


@cli.group("flow", help="Commands for finding and running flows for a project")
def flow():
    pass


@cli.group("service", help="Commands for connecting services to the keychain")
def service():
    pass


@cli.group("error", short_help="Get or share information about an error")
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


# Commands for group: project


def validate_project_name(value):
    if not re.match(r"^[a-zA-Z0-9_-]+$", value):
        raise click.UsageError(
            "Invalid project name. Allowed characters: "
            "letters, numbers, dash, and underscore"
        )
    return value


@project.command(
    name="init", help="Initialize a new project for use with the cumulusci toolbelt"
)
@pass_runtime(require_project=False)
def project_init(runtime):
    if not os.path.isdir(".git"):
        raise click.ClickException("You are not in the root of a Git repository")

    if os.path.isfile("cumulusci.yml"):
        raise click.ClickException("This project already has a cumulusci.yml file")

    context = {"cci_version": cumulusci.__version__}

    # Prep jinja2 environment for rendering files
    env = Environment(
        loader=PackageLoader(
            "cumulusci", os.path.join("files", "templates", "project")
        ),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Project and Package Info
    click.echo()
    click.echo(click.style("# Project Info", bold=True, fg="blue"))
    click.echo(
        "The following prompts will collect general information about the project"
    )

    project_name = os.path.split(os.getcwd())[-1:][0]
    click.echo()
    click.echo(
        "Enter the project name.  The name is usually the same as your repository name.  NOTE: Do not use spaces in the project name!"
    )
    context["project_name"] = click.prompt(
        click.style("Project Name", bold=True),
        default=project_name,
        value_proc=validate_project_name,
    )

    click.echo()
    click.echo(
        "CumulusCI uses an unmanaged package as a container for your project's metadata.  Enter the name of the package you want to use."
    )
    context["package_name"] = click.prompt(
        click.style("Package Name", bold=True), default=project_name
    )

    click.echo()
    context["package_namespace"] = None
    if click.confirm(
        click.style("Is this a managed package project?", bold=True), default=False
    ):
        click.echo(
            "Enter the namespace assigned to the managed package for this project"
        )
        context["package_namespace"] = click.prompt(
            click.style("Package Namespace", bold=True), default=project_name
        )

    click.echo()
    context["api_version"] = click.prompt(
        click.style("Salesforce API Version", bold=True),
        default=runtime.universal_config.project__package__api_version,
    )

    click.echo()
    click.echo(
        "Salesforce metadata can be stored using Metadata API format or DX source format. "
        "Which do you want to use?"
    )
    context["source_format"] = click.prompt(
        click.style("Source format", bold=True),
        type=click.Choice(["sfdx", "mdapi"]),
        default="sfdx",
    )

    # Dependencies
    dependencies = []
    click.echo(click.style("# Extend Project", bold=True, fg="blue"))
    click.echo(
        "CumulusCI makes it easy to build extensions of other projects configured for CumulusCI like Salesforce.org's NPSP and EDA.  If you are building an extension of another project using CumulusCI and have access to its Github repository, use this section to configure this project as an extension."
    )
    if click.confirm(
        click.style(
            "Are you extending another CumulusCI project such as NPSP or EDA?",
            bold=True,
        ),
        default=False,
    ):
        click.echo("Please select from the following options:")
        click.echo("  1: EDA (https://github.com/SalesforceFoundation/EDA)")
        click.echo("  2: NPSP (https://github.com/SalesforceFoundation/NPSP)")
        click.echo(
            "  3: Github URL (provide a URL to a Github repository configured for CumulusCI)"
        )
        selection = click.prompt(click.style("Enter your selection", bold=True))
        github_url = {
            "1": "https://github.com/SalesforceFoundation/EDA",
            "2": "https://github.com/SalesforceFoundation/NPSP",
        }.get(selection)
        if github_url is None:
            print(selection)
            github_url = click.prompt(
                click.style("Enter the Github Repository URL", bold=True)
            )
        dependencies.append({"type": "github", "url": github_url})
    context["dependencies"] = dependencies

    # Git Configuration
    git_config = {}
    click.echo()
    click.echo(click.style("# Git Configuration", bold=True, fg="blue"))
    click.echo(
        "CumulusCI assumes the current git branch is your default branch, your feature branches are named feature/*, your beta release tags are named beta/*, and your release tags are release/*.  If you want to use a different branch/tag naming scheme, you can configure the overrides here.  Otherwise, just accept the defaults."
    )

    default_main_branch = current_branch(os.getcwd()) or "main"
    git_default_branch = click.prompt(
        click.style("Default Branch", bold=True), default=default_main_branch
    )
    if (
        git_default_branch
        and git_default_branch != runtime.universal_config.project__git__default_branch
    ):
        git_config["default_branch"] = git_default_branch

    git_prefix_feature = click.prompt(
        click.style("Feature Branch Prefix", bold=True), default="feature/"
    )
    if (
        git_prefix_feature
        and git_prefix_feature != runtime.universal_config.project__git__prefix_feature
    ):
        git_config["prefix_feature"] = git_prefix_feature

    git_prefix_beta = click.prompt(
        click.style("Beta Tag Prefix", bold=True), default="beta/"
    )
    if (
        git_prefix_beta
        and git_prefix_beta != runtime.universal_config.project__git__prefix_beta
    ):
        git_config["prefix_beta"] = git_prefix_beta

    git_prefix_release = click.prompt(
        click.style("Release Tag Prefix", bold=True), default="release/"
    )
    if (
        git_prefix_release
        and git_prefix_release != runtime.universal_config.project__git__prefix_release
    ):
        git_config["prefix_release"] = git_prefix_release

    context["git"] = git_config

    #     test:
    click.echo()
    click.echo(click.style("# Apex Tests Configuration", bold=True, fg="blue"))
    click.echo(
        "The CumulusCI Apex test runner uses a SOQL where clause to select which tests to run.  Enter the SOQL pattern to use to match test class names."
    )

    test_name_match = click.prompt(
        click.style("Test Name Match", bold=True),
        default=runtime.universal_config.project__test__name_match,
    )
    if (
        test_name_match
        and test_name_match == runtime.universal_config.project__test__name_match
    ):
        test_name_match = None
    context["test_name_match"] = test_name_match

    context["code_coverage"] = None
    if click.confirm(
        click.style(
            "Do you want to check Apex code coverage when tests are run?", bold=True
        ),
        default=True,
    ):
        context["code_coverage"] = click.prompt(
            click.style("Minimum code coverage percentage", bold=True), default=75
        )

    # Render templates
    for name in (".gitignore", "README.md", "cumulusci.yml"):
        template = env.get_template(name)
        with open(name, "w") as f:
            f.write(template.render(**context))

    # Create source directory
    source_path = "force-app" if context["source_format"] == "sfdx" else "src"
    if not os.path.isdir(source_path):
        os.mkdir(source_path)

    # Create sfdx-project.json
    if not os.path.isfile("sfdx-project.json"):

        sfdx_project = {
            "packageDirectories": [{"path": "force-app", "default": True}],
            "namespace": context["package_namespace"],
            "sourceApiVersion": context["api_version"],
        }
        with open("sfdx-project.json", "w") as f:
            f.write(json.dumps(sfdx_project))

    # Create orgs subdir
    if not os.path.isdir("orgs"):
        os.mkdir("orgs")

    template = env.get_template("scratch_def.json")
    with open(os.path.join("orgs", "beta.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Beta Test Org",
                edition="Developer",
                managed=True,
            )
        )
    with open(os.path.join("orgs", "dev.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Dev Org",
                edition="Developer",
                managed=False,
            )
        )
    with open(os.path.join("orgs", "feature.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Feature Test Org",
                edition="Developer",
                managed=False,
            )
        )
    with open(os.path.join("orgs", "release.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Release Test Org",
                edition="Enterprise",
                managed=True,
            )
        )

    # create robot folder structure and starter files
    if not os.path.isdir("robot"):
        test_folder = os.path.join("robot", context["project_name"], "tests")
        resource_folder = os.path.join("robot", context["project_name"], "resources")
        doc_folder = os.path.join("robot", context["project_name"], "doc")

        os.makedirs(test_folder)
        os.makedirs(resource_folder)
        os.makedirs(doc_folder)
        test_src = os.path.join(
            cumulusci.__location__,
            "robotframework",
            "tests",
            "salesforce",
            "create_contact.robot",
        )
        test_dest = os.path.join(test_folder, "create_contact.robot")
        shutil.copyfile(test_src, test_dest)

    # Create pull request template
    if not os.path.isdir(".github"):
        os.mkdir(".github")
        with open(os.path.join(".github", "PULL_REQUEST_TEMPLATE.md"), "w") as f:
            f.write(
                """

# Critical Changes

# Changes

# Issues Closed
"""
            )

    # Create datasets folder
    if not os.path.isdir("datasets"):
        os.mkdir("datasets")
        template = env.get_template("mapping.yml")
        with open(os.path.join("datasets", "mapping.yml"), "w") as f:
            f.write(template.render(**context))

    click.echo(
        click.style(
            "Your project is now initialized for use with CumulusCI",
            bold=True,
            fg="green",
        )
    )


@project.command(
    name="info", help="Display information about the current project's configuration"
)
@pass_runtime
def project_info(runtime):
    render_recursive(runtime.project_config.project)


@project.command(
    name="dependencies",
    help="Displays the current dependencies for the project.  If the dependencies section has references to other github repositories, the repositories are inspected and a static list of dependencies is created",
)
@pass_runtime(require_keychain=True)
def project_dependencies(runtime):
    dependencies = runtime.project_config.get_static_dependencies()
    for line in runtime.project_config.pretty_dependencies(dependencies):
        click.echo(line)


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
        services = self._get_services_config(RUNTIME)
        return sorted(services.keys())

    def _build_param(self, attribute, details):
        req = details["required"]
        return click.Option((f"--{attribute}",), prompt=req, required=req)

    def get_command(self, ctx, name):
        runtime = RUNTIME
        runtime._load_keychain()
        services = self._get_services_config(RUNTIME)
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


# Commands for group: org


@org.command(
    name="browser",
    help="Opens a browser window and logs into the org using the stored OAuth credentials",
)
@click.argument("org_name", required=False)
@pass_runtime(require_project=False, require_keychain=True)
def org_browser(runtime, org_name):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)

    webbrowser.open(org_config.start_url)
    # Save the org config in case it was modified
    org_config.save()


@org.command(
    name="connect", help="Connects a new org's credentials using OAuth Web Flow"
)
@click.argument("org_name")
@click.option(
    "--sandbox", is_flag=True, help="If set, connects to a Salesforce sandbox org"
)
@click.option(
    "--login-url",
    help="If set, login to this hostname.",
    default="https://login.salesforce.com",
)
@click.option(
    "--default",
    is_flag=True,
    help="If set, sets the connected org as the new default org",
)
@click.option(
    "--global-org", help="Set True if org should be used by any project", is_flag=True
)
@pass_runtime(require_project=False, require_keychain=True)
def org_connect(runtime, org_name, sandbox, login_url, default, global_org):
    runtime.check_org_overwrite(org_name)

    if "lightning.force.com" in login_url:
        raise click.UsageError(
            "Connecting an org with a lightning.force.com URL does not work. "
            "Use the my.salesforce.com version instead"
        )

    connected_app = runtime.keychain.get_service("connected_app")
    if sandbox:
        login_url = "https://test.salesforce.com"

    oauth_capture = CaptureSalesforceOAuth(
        client_id=connected_app.client_id,
        client_secret=connected_app.client_secret,
        callback_url=connected_app.callback_url,
        auth_site=login_url,
        scope="web full refresh_token",
    )
    oauth_dict = oauth_capture()
    global_org = global_org or runtime.project_config is None
    org_config = OrgConfig(oauth_dict, org_name, runtime.keychain, global_org)
    org_config.load_userinfo()
    org_config._load_orginfo()
    if org_config.organization_sobject["TrialExpirationDate"] is None:
        org_config.config["expires"] = "Persistent"
    else:
        org_config.config["expires"] = parse_api_datetime(
            org_config.organization_sobject["TrialExpirationDate"]
        ).date()

    org_config.save()

    if default and runtime.project_config is not None:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")


@org.command(name="default", help="Sets an org as the default org for tasks and flows")
@click.argument("org_name")
@click.option(
    "--unset",
    is_flag=True,
    help="Unset the org as the default org leaving no default org selected",
)
@pass_runtime(require_keychain=True)
def org_default(runtime, org_name, unset):
    if unset:
        runtime.keychain.unset_default_org()
        click.echo(f"{org_name} is no longer the default org.  No default org set.")
    else:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")


@org.command(name="import", help="Import a scratch org from Salesforce DX")
@click.argument("username_or_alias")
@click.argument("org_name")
@pass_runtime(require_keychain=True)
def org_import(runtime, username_or_alias, org_name):
    org_config = {"username": username_or_alias}
    scratch_org_config = ScratchOrgConfig(
        org_config, org_name, runtime.keychain, global_org=False
    )
    scratch_org_config.config["created"] = True

    info = scratch_org_config.scratch_info
    scratch_org_config.config["days"] = calculate_org_days(info)
    scratch_org_config.config["date_created"] = parse_api_datetime(info["created_date"])

    scratch_org_config.save()
    click.echo(
        "Imported scratch org: {org_id}, username: {username}".format(
            **scratch_org_config.scratch_info
        )
    )


def calculate_org_days(info):
    """Returns the difference in days between created_date (ISO 8601),
    and expiration_date (%Y-%m-%d)"""
    if not info.get("created_date") or not info.get("expiration_date"):
        return 1
    created_date = parse_api_datetime(info["created_date"]).date()
    expires_date = datetime.strptime(info["expiration_date"], "%Y-%m-%d").date()
    return abs((expires_date - created_date).days)


@org.command(name="info", help="Display information for a connected org")
@click.argument("org_name", required=False)
@click.option(
    "print_json", "--json", is_flag=True, help="Print as JSON.  Includes access token"
)
@pass_runtime(require_project=False, require_keychain=True)
def org_info(runtime, org_name, print_json):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)

    if print_json:
        click.echo(
            json.dumps(
                org_config.config,
                sort_keys=True,
                indent=4,
                default=str,
                separators=(",", ": "),
            )
        )
    else:
        UI_KEYS = [
            "config_file",
            "config_name",
            "created",
            "date_created",
            "days",
            "default",
            "email_address",
            "instance_url",
            "instance_name",
            "is_sandbox",
            "namespaced",
            "org_id",
            "org_type",
            "password",
            "scratch",
            "scratch_org_type",
            "set_password",
            "sfdx_alias",
            "username",
        ]
        keys = [key for key in org_config.config.keys() if key in UI_KEYS]
        pairs = [[key, str(org_config.config[key])] for key in keys]
        pairs.append(["api_version", org_config.latest_api_version])
        pairs.sort()
        table_data = [["Key", "Value"]]
        table_data.extend(
            [[click.style(key, bold=True), value] for key, value in pairs]
        )
        table = CliTable(table_data, wrap_cols=["Value"])
        table.echo()

        if org_config.scratch and org_config.expires:
            click.echo("Org expires on {:%c}".format(org_config.expires))

    # Save the org config in case it was modified
    org_config.save()


@org.command(name="list", help="Lists the connected orgs for the current project")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@pass_runtime(require_project=False, require_keychain=True)
def org_list(runtime, plain):
    plain = plain or runtime.universal_config.cli__plain_output
    header = ["Name", "Default", "Username", "Expires"]
    persistent_data = [header]
    scratch_data = [header[:2] + ["Days", "Expired", "Config", "Domain"]]
    org_configs = {
        org: runtime.keychain.get_org(org) for org in runtime.keychain.list_orgs()
    }
    rows_to_dim = []
    default_org_name, _ = runtime.keychain.get_default_org()
    for org, org_config in org_configs.items():
        row = [org, org == default_org_name]
        if isinstance(org_config, ScratchOrgConfig):
            org_days = org_config.format_org_days()
            if org_config.expired:
                domain = ""
            else:
                instance_url = org_config.config.get("instance_url", "")
                domain = urlparse(instance_url).hostname or ""
                if domain:
                    domain = domain.replace(".my.salesforce.com", "")
            row.extend(
                [org_days, not org_config.active, org_config.config_name, domain]
            )
            scratch_data.append(row)
        else:
            username = org_config.config.get(
                "username", org_config.userinfo__preferred_username
            )
            row.append(username)
            row.append(org_config.expires or "Unknown")
            persistent_data.append(row)

    rows_to_dim = [row_index for row_index, row in enumerate(scratch_data) if row[3]]
    scratch_table = CliTable(
        scratch_data, title="Scratch Orgs", bool_cols=["Default"], dim_rows=rows_to_dim
    )
    scratch_table.stringify_boolean_col(col_name="Expired", true_str=CROSSMARK)
    scratch_table.echo(plain)

    wrap_cols = ["Username"] if not plain else None
    persistent_table = CliTable(
        persistent_data,
        title="Connected Orgs",
        wrap_cols=wrap_cols,
        bool_cols=["Default"],
    )
    persistent_table.echo(plain)


@org.command(
    name="prune", help="Removes all expired scratch orgs from the current project"
)
@click.option(
    "--include-active",
    is_flag=True,
    help="Remove all scratch orgs, regardless of expiry.",
)
@pass_runtime(require_project=True, require_keychain=True)
def org_prune(runtime, include_active=False):

    predefined_scratch_configs = getattr(runtime.project_config, "orgs__scratch", {})

    expired_orgs_removed = []
    active_orgs_removed = []
    org_shapes_skipped = []
    active_orgs_skipped = []
    for org_name in runtime.keychain.list_orgs():

        org_config = runtime.keychain.get_org(org_name)

        if org_name in predefined_scratch_configs:
            if org_config.active and include_active:
                runtime.keychain.remove_org(org_name)
                active_orgs_removed.append(org_name)
            else:
                org_shapes_skipped.append(org_name)

        elif org_config.active:
            if include_active:
                runtime.keychain.remove_org(org_name)
                active_orgs_removed.append(org_name)
            else:
                active_orgs_skipped.append(org_name)

        elif isinstance(org_config, ScratchOrgConfig):
            runtime.keychain.remove_org(org_name)
            expired_orgs_removed.append(org_name)

    if expired_orgs_removed:
        click.echo(
            f"Successfully removed {len(expired_orgs_removed)} expired scratch orgs: {', '.join(expired_orgs_removed)}"
        )
    else:
        click.echo("No expired scratch orgs to delete. ✨")

    if active_orgs_removed:
        click.echo(
            f"Successfully removed {len(active_orgs_removed)} active scratch orgs: {', '.join(active_orgs_removed)}"
        )
    elif include_active:
        click.echo("No active scratch orgs to delete. ✨")

    if org_shapes_skipped:
        click.echo(f"Skipped org shapes: {', '.join(org_shapes_skipped)}")

    if active_orgs_skipped:
        click.echo(f"Skipped active orgs: {', '.join(active_orgs_skipped)}")


@org.command(name="remove", help="Removes an org from the keychain")
@click.argument("org_name")
@click.option(
    "--global-org",
    is_flag=True,
    help="Set this option to force remove a global org.  Default behavior is to error if you attempt to delete a global org.",
)
@pass_runtime(require_project=False, require_keychain=True)
def org_remove(runtime, org_name, global_org):
    try:
        org_config = runtime.keychain.get_org(org_name)
    except OrgNotFound:
        raise click.ClickException(f"Org {org_name} does not exist in the keychain")

    if org_config.can_delete():
        click.echo("A scratch org was already created, attempting to delete...")
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo("Deleting scratch org failed with error:")
            click.echo(e)

    global_org = global_org or runtime.project_config is None
    runtime.keychain.remove_org(org_name, global_org)


@org.command(
    name="scratch", help="Connects a Salesforce DX Scratch Org to the keychain"
)
@click.argument("config_name")
@click.argument("org_name")
@click.option(
    "--default",
    is_flag=True,
    help="If set, sets the connected org as the new default org",
)
@click.option(
    "--devhub", help="If provided, overrides the devhub used to create the scratch org"
)
@click.option(
    "--days",
    help="If provided, overrides the scratch config default days value for how many days the scratch org should persist",
)
@click.option(
    "--no-password", is_flag=True, help="If set, don't set a password for the org"
)
@pass_runtime(require_keychain=True)
def org_scratch(runtime, config_name, org_name, default, devhub, days, no_password):
    runtime.check_org_overwrite(org_name)

    scratch_configs = getattr(runtime.project_config, "orgs__scratch")
    if not scratch_configs:
        raise click.UsageError("No scratch org configs found in cumulusci.yml")
    scratch_config = scratch_configs.get(config_name)
    if not scratch_config:
        raise click.UsageError(
            f"No scratch org config named {config_name} found in the cumulusci.yml file"
        )

    if devhub:
        scratch_config["devhub"] = devhub

    runtime.keychain.create_scratch_org(
        org_name, config_name, days, set_password=not (no_password)
    )

    if default:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")
    else:
        click.echo(f"{org_name} is configured for use")


@org.command(
    name="scratch_delete",
    help="Deletes a Salesforce DX Scratch Org leaving the config in the keychain for regeneration",
)
@click.argument("org_name")
@pass_runtime(require_keychain=True)
def org_scratch_delete(runtime, org_name):
    org_config = runtime.keychain.get_org(org_name)
    if not org_config.scratch:
        raise click.UsageError(f"Org {org_name} is not a scratch org")

    org_config.delete_org()

    org_config.save()


org_shell_cci_help_message = """
The cumulusci shell gives you access to the following objects and functions:

* sf - simple_salesforce connected to your org. [1]
* org_config - local information about your org. [2]
* project_config - information about your project. [3]
* tooling - simple_salesforce connected to the tooling API on your org.
* query() - SOQL query. `help(query)` for more information
* describe() - Inspect object fields. `help(describe)` for more information
* help() - for interactive help on Python
* help(obj) - for help on any specific Python object or module

[1] https://github.com/simple-salesforce/simple-salesforce
[2] https://cumulusci.readthedocs.io/en/latest/api/cumulusci.core.config.html#module-cumulusci.core.config.OrgConfig
[3] https://cumulusci.readthedocs.io/en/latest/api/cumulusci.core.config.html#module-cumulusci.core.config.project_config
"""


class CCIHelp(type(help)):
    def __repr__(self):
        return org_shell_cci_help_message


@org.command(
    name="shell",
    help="Drop into a Python shell with a simple_salesforce connection in `sf`, "
    "as well as the `org_config` and `project_config`.",
)
@click.argument("org_name", required=False)
@click.option("--script", help="Path to a script to run", type=click.Path())
@click.option("--python", help="Python code to run directly")
@pass_runtime(require_keychain=True)
def org_shell(runtime, org_name, script=None, python=None):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)

    sf = get_simple_salesforce_connection(runtime.project_config, org_config)
    tooling = get_simple_salesforce_connection(
        runtime.project_config, org_config, base_url="tooling"
    )

    sf_helpers = SimpleSalesforceUIHelpers(sf)

    globals = {
        "sf": sf,
        "tooling": tooling,
        "org_config": org_config,
        "project_config": runtime.project_config,
        "help": CCIHelp(),
        "query": sf_helpers.query,
        "describe": sf_helpers.describe,
    }

    if script:
        if python:
            raise click.UsageError("Cannot specify both --script and --python")
        runpy.run_path(script, init_globals=globals)
    elif python:
        exec(python, globals)
    else:
        code.interact(
            banner=f"Use `sf` to access org `{org_name}` via simple_salesforce\n"
            + "Type `help` for more information about the cci shell.",
            local=globals,
        )

    # Save the org config in case it was modified
    org_config.save()


# Commands for group: task


@task.command(name="list", help="List available tasks for the current context")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=False)
def task_list(runtime, plain, print_json):
    task_groups = {}
    tasks = (
        runtime.project_config.list_tasks()
        if runtime.project_config is not None
        else runtime.universal_config.list_tasks()
    )
    plain = plain or runtime.universal_config.cli__plain_output

    if print_json:
        click.echo(json.dumps(tasks))
        return None

    for task in tasks:
        group = task["group"] or "Other"
        if group not in task_groups:
            task_groups[group] = []
        task_groups[group].append([task["name"], task["description"]])

    for group, tasks in task_groups.items():
        data = [["Task", "Description"]]
        data.extend(sorted(tasks))
        table = CliTable(data, group, wrap_cols=["Description"])
        table.echo(plain)

    click.echo(
        "Use "
        + click.style("cci task info <task_name>", bold=True)
        + " to get more information about a task."
    )


@task.command(name="doc", help="Exports RST format documentation for all tasks")
@pass_runtime(require_project=False)
def task_doc(runtime):
    config_src = runtime.universal_config

    click.echo("==========================================")
    click.echo("Tasks Reference")
    click.echo("==========================================")
    click.echo("")

    for name, options in config_src.tasks.items():
        task_config = TaskConfig(options)
        doc = doc_task(name, task_config)
        click.echo(doc)
        click.echo("")


@task.command(name="info", help="Displays information for a task")
@click.argument("task_name")
@pass_runtime(require_project=False, require_keychain=True)
def task_info(runtime, task_name):
    task_config = (
        runtime.project_config.get_task(task_name)
        if runtime.project_config is not None
        else runtime.universal_config.get_task(task_name)
    )

    doc = doc_task(task_name, task_config).encode()
    click.echo(rst2ansi(doc))


@task.command(name="run", help="Runs a task")
@click.argument("task_name")
@click.option(
    "--org",
    help="Specify the target org.  By default, runs against the current default org",
)
@click.option(
    "-o",
    nargs=2,
    multiple=True,
    help="Pass task specific options for the task as '-o option value'.  You can specify more than one option by using -o more than once.",
)
@click.option(
    "--debug", is_flag=True, help="Drops into pdb, the Python debugger, on an exception"
)
@click.option(
    "--debug-before",
    is_flag=True,
    help="Drops into the Python debugger right before task start.",
)
@click.option(
    "--debug-after",
    is_flag=True,
    help="Drops into the Python debugger at task completion.",
)
@click.option(
    "--no-prompt",
    is_flag=True,
    help="Disables all prompts.  Set for non-interactive mode use such as calling from scripts or CI systems",
)
@pass_runtime(require_keychain=True)
def task_run(runtime, task_name, org, o, debug, debug_before, debug_after, no_prompt):

    # Get necessary configs
    org, org_config = runtime.get_org(org, fail_if_missing=False)
    task_config = runtime.project_config.get_task(task_name)

    # Get the class to look up options
    class_path = task_config.class_path
    task_class = import_global(class_path)

    # Parse command line options and add to task config
    if o:
        if "options" not in task_config.config:
            task_config.config["options"] = {}
        for name, value in o:
            # Validate the option
            if name not in task_class.task_options:
                raise click.UsageError(
                    f'Option "{name}" is not available for task {task_name}'
                )

            # Override the option in the task config
            task_config.config["options"][name] = value

    # Create and run the task
    try:
        task = task_class(
            task_config.project_config, task_config, org_config=org_config
        )

        if debug_before:
            import pdb

            pdb.set_trace()

        task()

        if debug_after:
            import pdb

            pdb.set_trace()
    finally:
        runtime.alert(f"Task complete: {task_name}")


# Commands for group: flow


@flow.command(name="list", help="List available flows for the current context")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=False)
def flow_list(runtime, plain, print_json):
    plain = plain or runtime.universal_config.cli__plain_output
    flows = (
        runtime.project_config.list_flows()
        if runtime.project_config is not None
        else runtime.universal_config.list_flows()
    )

    if print_json:
        click.echo(json.dumps(flows))
        return None

    data = [["Name", "Description"]]
    data.extend([flow["name"], flow["description"]] for flow in flows)

    table = CliTable(data, title="Flows", wrap_cols=["Description"])
    table.echo(plain=plain)

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
        coordinator.run(org_config)
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


CCI_LOGFILE_PATH = Path.home() / ".cumulusci" / "logs" / "cci.log"


@error.command(
    name="info",
    help="Outputs the last part of the most recent traceback (if one exists in the most recent log)",
)
@click.option("--max-lines", "-m", default=30, show_default=True, type=int)
def error_info(max_lines):
    if not CCI_LOGFILE_PATH.is_file():
        click.echo(f"No logfile found at: {CCI_LOGFILE_PATH}")
    else:
        output = lines_from_traceback(CCI_LOGFILE_PATH.read_text(), max_lines)
        click.echo(output)


def lines_from_traceback(log_content, num_lines):
    """Returns the the last max_lines of the logfile,
    or the whole traceback, whichever is shorter. If
    no stacktrace is found in the logfile, the user is
    notified.
    """
    stacktrace_start = "Traceback (most recent call last):"
    if stacktrace_start not in log_content:
        return f"\nNo stacktrace found in: {CCI_LOGFILE_PATH}\n"

    stacktrace = ""
    for line in reversed(log_content.split("\n")):
        stacktrace = "\n" + line + stacktrace
        if stacktrace_start in line:
            break
        num_lines -= 1
        if num_lines == -1:
            break

    return stacktrace


@error.command(name="gist", help="Creates a GitHub gist from the latest logfile")
@pass_runtime(require_project=False, require_keychain=True)
def gist(runtime):
    if CCI_LOGFILE_PATH.is_file():
        log_content = CCI_LOGFILE_PATH.read_text()
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
        gh = RUNTIME.keychain.get_service("github")
        gist = create_gist(
            get_github_api(gh.config["username"], gh.config["password"]),
            "CumulusCI Error Output",
            files,
        )
    except github3.exceptions.NotFoundError:
        raise CumulusCIException(GIST_404_ERR_MSG)
    except Exception as e:
        raise CumulusCIException(
            f"An error occurred attempting to create your gist:\n{e}"
        )
    else:
        click.echo(f"Gist created: {gist.html_url}")
        webbrowser.open(gist.html_url)
