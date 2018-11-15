from __future__ import absolute_import
from future import standard_library

standard_library.install_aliases()
from past.builtins import basestring
from builtins import str
from builtins import object
from collections import OrderedDict
import functools
import json
import operator
import os
import sys
import webbrowser
import code
import yaml
import time

from contextlib import contextmanager
from shutil import copyfile

import click
import pkg_resources
import requests
from plaintable import Table
from rst2ansi import rst2ansi
from jinja2 import Environment
from jinja2 import PackageLoader

import cumulusci
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import BaseConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import ScratchOrgConfig
from cumulusci.core.config import ServiceConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import CumulusCIFailure
from cumulusci.core.exceptions import CumulusCIUsageError
from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.exceptions import ScratchOrgException
from cumulusci.core.exceptions import ServiceNotConfigured
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.flows import BaseFlow
from cumulusci.core.utils import import_class
from cumulusci.cli.config import CliConfig
from cumulusci.cli.config import get_installed_version
from cumulusci.utils import doc_task
from cumulusci.oauth.salesforce import CaptureSalesforceOAuth
from .logger import init_logger
import re


@contextmanager
def timestamp_file():
    """Opens a file for tracking the time of the last version check"""
    config_dir = os.path.join(
        os.path.expanduser("~"), BaseGlobalConfig.config_local_dir
    )

    if not os.path.exists(config_dir):
        os.mkdir(config_dir)

    with open(os.path.join(config_dir, "cumulus_timestamp"), "w+") as f:
        yield f


FINAL_VERSION_RE = re.compile(r"^[\d\.]+$")


def is_final_release(version):
    """Returns bool whether version string should be considered a final release.

    cumulusci versions are considered final if they contain only digits and periods.
    e.g. 1.0.1 is final but 2.0b1 and 2.0.dev0 are not.
    """
    return FINAL_VERSION_RE.match(version)


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
                "An update to CumulusCI is available. Use pip install --upgrade cumulusci to update."
            )


def handle_exception_debug(config, debug, throw_exception=None, no_prompt=None):
    if debug:
        import pdb
        import traceback

        traceback.print_exc()
        pdb.post_mortem()
    else:
        if throw_exception:
            raise throw_exception
        else:
            handle_sentry_event(config, no_prompt)
            raise


def render_recursive(data, indent=None):
    if indent is None:
        indent = 0
    indent_str = " " * indent
    if isinstance(data, BaseConfig):
        render_recursive(data.config)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, basestring):
                click.echo("{}- {}".format(indent_str, item))
            else:
                click.echo("{}-".format(indent_str))
                render_recursive(item, indent=indent + 4)
    elif isinstance(data, dict):
        for key, value in data.items():
            key_str = click.style(str(key) + ":", bold=True)
            if isinstance(value, list):
                click.echo("{}{}".format(indent_str, key_str))
                render_recursive(value, indent=indent + 4)
            elif isinstance(value, dict):
                click.echo("{}{}".format(indent_str, key_str))
                render_recursive(value, indent=indent + 4)
            else:
                click.echo("{}{} {}".format(indent_str, key_str, value))


def handle_sentry_event(config, no_prompt):
    event = config.project_config.sentry_event
    if not event:
        return

    sentry_config = config.project_config.keychain.get_service("sentry")
    event_url = "{}/{}/{}/?query={}".format(
        config.project_config.sentry.remote.base_url,
        sentry_config.org_slug,
        sentry_config.project_slug,
        event,
    )
    click.echo(
        "An error event was recorded in sentry.io and can be viewed at the url:\n{}".format(
            event_url
        )
    )

    if not no_prompt and click.confirm(
        click.style(
            "Do you want to open a browser to view the error in sentry.io?", bold=True
        )
    ):
        webbrowser.open(event_url)


# hook for tests
TEST_CONFIG = None


def load_config(load_project_config=True, load_keychain=True):
    try:
        config = TEST_CONFIG or CliConfig(
            load_project_config=load_project_config, load_keychain=load_keychain
        )
        config.check_cumulusci_version()
    except click.UsageError as e:
        click.echo(str(e))
        sys.exit(1)
    return config


def pass_config(func=None, **config_kw):
    """Decorator which passes the CCI config object as the first arg to a click command."""

    def decorate(func):
        def new_func(*args, **kw):
            config = load_config(**config_kw)
            func(config, *args, **kw)

        return functools.update_wrapper(new_func, func)

    if func is None:
        return decorate
    else:
        return decorate(func)


# Root command


@click.group("main", help="")
def main():
    """Main CumulusCI CLI entry point.

    This runs as the first step in processing any CLI command.
    """
    check_latest_version()
    init_logger()


@click.command(name="version", help="Print the current version of CumulusCI")
def version():
    click.echo(cumulusci.__version__)


@click.command(name="shell", help="Drop into a python shell")
def shell():
    try:
        config = load_config(load_project_config=True, load_keychain=True)
    except SystemExit:
        config = load_config(load_project_config=False, load_keychain=False)

    code.interact(local=dict(globals(), **locals()))


# Top Level Groups


@click.group(
    "project", help="Commands for interacting with project repository configurations"
)
def project():
    pass


@click.group("org", help="Commands for connecting and interacting with Salesforce orgs")
def org():
    pass


@click.group("task", help="Commands for finding and running tasks for a project")
def task():
    pass


@click.group("flow", help="Commands for finding and running flows for a project")
def flow():
    pass


@click.group("service", help="Commands for connecting services to the keychain")
def service():
    pass


main.add_command(project)
main.add_command(org)
main.add_command(task)
main.add_command(flow)
main.add_command(version)
main.add_command(shell)
main.add_command(service)


# Commands for group: project


@click.command(
    name="init", help="Initialize a new project for use with the cumulusci toolbelt"
)
@pass_config(load_project_config=False)
def project_init(config):
    if not os.path.isdir(".git"):
        raise click.ClickException("You are not in the root of a Git repository")

    if os.path.isfile("cumulusci.yml"):
        raise click.ClickException("This project already has a cumulusci.yml file")

    context = {}

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
        click.style("Project Name", bold=True), default=project_name
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
        default=config.global_config.project__package__api_version,
    )

    # Dependencies
    dependencies = []
    click.echo(click.style("# Extend Project", bold=True, fg="blue"))
    click.echo(
        "CumulusCI makes it easy to build extensions of other projects configured for CumulusCI like Salesforce.org's NPSP and HEDA.  If you are building an extension of another project using CumulusCI and have access to its Github repository, use this section to configure this project as an extension."
    )
    if click.confirm(
        click.style(
            "Are you extending another CumulusCI project such as NPSP or HEDA?",
            bold=True,
        ),
        default=False,
    ):
        click.echo("Please select from the following options:")
        click.echo("  1: HEDA (https://github.com/SalesforceFoundation/HEDAP)")
        click.echo("  2: NPSP (https://github.com/SalesforceFoundation/Cumulus)")
        click.echo(
            "  3: Github URL (provide a URL to a Github repository configured for CumulusCI)"
        )
        selection = click.prompt(click.style("Enter your selection", bold=True))
        github_url = {
            "1": "https://github.com/SalesforceFoundation/HEDAP",
            "2": "https://github.com/SalesforceFoundation/Cumulus",
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
        "CumulusCI assumes your default branch is master, your feature branches are named feature/*, your beta release tags are named beta/*, and your release tags are release/*.  If you want to use a different branch/tag naming scheme, you can configure the overrides here.  Otherwise, just accept the defaults."
    )

    git_default_branch = click.prompt(
        click.style("Default Branch", bold=True), default="master"
    )
    if (
        git_default_branch
        and git_default_branch != config.global_config.project__git__default_branch
    ):
        git_config["default_branch"] = git_default_branch

    git_prefix_feature = click.prompt(
        click.style("Feature Branch Prefix", bold=True), default="feature/"
    )
    if (
        git_prefix_feature
        and git_prefix_feature != config.global_config.project__git__prefix_feature
    ):
        git_config["prefix_feature"] = git_prefix_feature

    git_prefix_beta = click.prompt(
        click.style("Beta Tag Prefix", bold=True), default="beta/"
    )
    if (
        git_prefix_beta
        and git_prefix_beta != config.global_config.project__git__prefix_beta
    ):
        git_config["prefix_beta"] = git_prefix_beta

    git_prefix_release = click.prompt(
        click.style("Release Tag Prefix", bold=True), default="release/"
    )
    if (
        git_prefix_release
        and git_prefix_release != config.global_config.project__git__prefix_release
    ):
        git_config["prefix_release"] = git_prefix_release

    context["git"] = git_config

    #     test:
    test_config = []
    click.echo()
    click.echo(click.style("# Apex Tests Configuration", bold=True, fg="blue"))
    click.echo(
        "The CumulusCI Apex test runner uses a SOQL where clause to select which tests to run.  Enter the SOQL pattern to use to match test class names."
    )

    test_name_match = click.prompt(
        click.style("Test Name Match", bold=True),
        default=config.global_config.project__test__name_match,
    )
    if (
        test_name_match
        and test_name_match == config.global_config.project__test__name_match
    ):
        test_name_match = None
    context["test_name_match"] = test_name_match

    # Render the cumulusci.yml file
    template = env.get_template("cumulusci.yml")
    with open("cumulusci.yml", "w") as f:
        f.write(template.render(**context))

    # Create src directory
    if not os.path.isdir("src"):
        os.mkdir("src")

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
            )
        )
    with open(os.path.join("orgs", "dev.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Dev Org",
                edition="Developer",
            )
        )
    with open(os.path.join("orgs", "feature.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Feature Test Org",
                edition="Developer",
            )
        )
    with open(os.path.join("orgs", "release.json"), "w") as f:
        f.write(
            template.render(
                package_name=context["package_name"],
                org_name="Release Test Org",
                edition="Enterprise",
            )
        )

    # Create initial create_contact.robot test
    if not os.path.isdir("tests"):
        os.mkdir("tests")
        test_folder = os.path.join("tests", "standard_objects")
        os.mkdir(test_folder)
        test_src = os.path.join(
            cumulusci.__location__,
            "robotframework",
            "tests",
            "salesforce",
            "create_contact.robot",
        )
        test_dest = os.path.join(test_folder, "create_contact.robot")
        copyfile(test_src, test_dest)

    click.echo(
        click.style(
            "Your project is now initialized for use with CumulusCI",
            bold=True,
            fg="green",
        )
    )
    click.echo(
        click.style(
            "You can use the project edit command to edit the project's config file",
            fg="yellow",
        )
    )


@click.command(
    name="info", help="Display information about the current project's configuration"
)
@pass_config(load_keychain=False)
def project_info(config):
    render_recursive(config.project_config.project)


@click.command(
    name="dependencies",
    help="Displays the current dependencies for the project.  If the dependencies section has references to other github repositories, the repositories are inspected and a static list of dependencies is created",
)
@pass_config
def project_dependencies(config):
    dependencies = config.project_config.get_static_dependencies()
    for line in config.project_config.pretty_dependencies(dependencies):
        click.echo(line)


project.add_command(project_init)
project.add_command(project_info)
project.add_command(project_dependencies)


# Commands for group: service


@click.command(name="list", help="List services available for configuration and use")
@pass_config
def service_list(config):
    headers = ["service", "description", "is_configured"]
    data = []
    for serv, schema in list(config.project_config.services.items()):
        is_configured = ""
        if serv in config.keychain.list_services():
            is_configured = "* "
        data.append((serv, schema["description"], is_configured))
    table = Table(data, headers)
    click.echo(table)


class ConnectServiceCommand(click.MultiCommand):
    def list_commands(self, ctx):
        """ list the services that can be configured """
        config = load_config()
        return sorted(config.project_config.services.keys())

    def _build_param(self, attribute, details):
        req = details["required"]
        return click.Option(("--{0}".format(attribute),), prompt=req, required=req)

    def get_command(self, ctx, name):
        config = load_config()

        attributes = iter(
            list(
                getattr(
                    config.project_config, "services__{0}__attributes".format(name)
                ).items()
            )
        )
        params = [self._build_param(attr, cnfg) for attr, cnfg in attributes]
        params.append(click.Option(("--project",), is_flag=True))

        def callback(project=False, *args, **kwargs):
            serv_conf = dict(
                (k, v) for k, v in list(kwargs.items()) if v != None
            )  # remove None values
            config.keychain.set_service(name, ServiceConfig(serv_conf), project)
            if project:
                click.echo("{0} is now configured for this project".format(name))
            else:
                click.echo("{0} is now configured for global use".format(name))

        ret = click.Command(name, params=params, callback=callback)
        return ret


@click.command(
    cls=ConnectServiceCommand, name="connect", help="Connect a CumulusCI task service"
)
def service_connect():
    pass


@click.command(name="info", help="Show the details of a connected service")
@click.argument("service_name")
@pass_config
def service_info(config, service_name):
    try:
        service_config = config.keychain.get_service(service_name)
        render_recursive(service_config.config)
    except ServiceNotConfigured:
        click.echo(
            "{0} is not configured for this project.  Use service connect {0} to configure.".format(
                service_name
            )
        )


service.add_command(service_connect)
service.add_command(service_list)
service.add_command(service_info)


# Commands for group: org


@click.command(
    name="browser",
    help="Opens a browser window and logs into the org using the stored OAuth credentials",
)
@click.argument("org_name", required=False)
@pass_config
def org_browser(config, org_name):
    org_name, org_config = config.get_org(org_name)
    org_config.refresh_oauth_token(config.keychain)

    webbrowser.open(org_config.start_url)

    # Save the org config in case it was modified
    config.keychain.set_org(org_config)


@click.command(
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
@pass_config
def org_connect(config, org_name, sandbox, login_url, default, global_org):
    config.check_org_overwrite(org_name)

    try:
        connected_app = config.keychain.get_service("connected_app")
    except ServiceNotConfigured as e:
        raise ServiceNotConfigured(
            "Connected App is required but not configured. "
            + "Configure the Connected App service:\n"
            + "http://cumulusci.readthedocs.io/en/latest/"
            + "tutorial.html#configuring-the-project-s-connected-app"
        )
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
    org_config = OrgConfig(oauth_dict, org_name)
    org_config.load_userinfo()

    config.keychain.set_org(org_config, global_org)

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo("{} is now the default org".format(org_name))


@click.command(
    name="default", help="Sets an org as the default org for tasks and flows"
)
@click.argument("org_name")
@click.option(
    "--unset",
    is_flag=True,
    help="Unset the org as the default org leaving no default org selected",
)
@pass_config
def org_default(config, org_name, unset):

    if unset:
        config.keychain.unset_default_org()
        click.echo(
            "{} is no longer the default org.  No default org set.".format(org_name)
        )
    else:
        config.keychain.set_default_org(org_name)
        click.echo("{} is now the default org".format(org_name))


@click.command(name="import", help="Import a scratch org from Salesforce DX")
@click.argument("username_or_alias")
@click.argument("org_name")
@pass_config
def org_import(config, username_or_alias, org_name):
    org_config = {"username": username_or_alias}
    scratch_org_config = ScratchOrgConfig(org_config, org_name)
    scratch_org_config.config["created"] = True
    config.keychain.set_org(scratch_org_config)
    click.echo(
        "Imported scratch org: {org_id}, username: {username}".format(
            **scratch_org_config.scratch_info
        )
    )


@click.command(name="info", help="Display information for a connected org")
@click.argument("org_name", required=False)
@click.option("print_json", "--json", is_flag=True, help="Print as JSON")
@pass_config
def org_info(config, org_name, print_json):
    org_name, org_config = config.get_org(org_name)
    org_config.refresh_oauth_token(config.keychain)

    if print_json:
        click.echo(json.dumps(org_config.config, sort_keys=True, indent=4))
    else:
        render_recursive(org_config.config)

        if org_config.scratch and org_config.expires:
            click.echo("Org expires on {:%c}".format(org_config.expires))

    # Save the org config in case it was modified
    config.keychain.set_org(org_config)


@click.command(name="list", help="Lists the connected orgs for the current project")
@pass_config
def org_list(config):
    data = []
    headers = [
        "org",
        "default",
        "scratch",
        "days",
        "expired",
        "config_name",
        "username",
    ]
    for org in config.project_config.keychain.list_orgs():
        org_config = config.project_config.keychain.get_org(org)
        row = [org]
        row.append("*" if org_config.default else "")
        row.append("*" if org_config.scratch else "")
        if org_config.days_alive:
            row.append(
                "{} of {}".format(org_config.days_alive, org_config.days)
                if org_config.scratch
                else ""
            )
        else:
            row.append(org_config.days if org_config.scratch else "")
        row.append("*" if org_config.scratch and org_config.expired else "")
        row.append(org_config.config_name if org_config.config_name else "")
        username = org_config.config.get(
            "username", org_config.userinfo__preferred_username
        )
        row.append(username if username else "")
        data.append(row)
    table = Table(data, headers)
    click.echo(table)


@click.command(name="remove", help="Removes an org from the keychain")
@click.argument("org_name")
@click.option(
    "--global-org",
    is_flag=True,
    help="Set this option to force remove a global org.  Default behavior is to error if you attempt to delete a global org.",
)
@pass_config
def org_remove(config, org_name, global_org):
    try:
        org_config = config.keychain.get_org(org_name)
    except OrgNotFound:
        raise click.ClickException(
            "Org {} does not exist in the keychain".format(org_name)
        )

    if org_config.can_delete():
        click.echo("A scratch org was already created, attempting to delete...")
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo("Deleting scratch org failed with error:")
            click.echo(e)

    config.keychain.remove_org(org_name, global_org)


@click.command(
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
@pass_config
def org_scratch(config, config_name, org_name, default, devhub, days, no_password):
    config.check_org_overwrite(org_name)

    scratch_configs = getattr(config.project_config, "orgs__scratch")
    if not scratch_configs:
        raise click.UsageError("No scratch org configs found in cumulusci.yml")
    scratch_config = scratch_configs.get(config_name)
    if not scratch_config:
        raise click.UsageError(
            "No scratch org config named {} found in the cumulusci.yml file".format(
                config_name
            )
        )

    if devhub:
        scratch_config["devhub"] = devhub

    config.keychain.create_scratch_org(
        org_name, config_name, days, set_password=not (no_password)
    )

    if default:
        org = config.keychain.set_default_org(org_name)
        click.echo("{} is now the default org".format(org_name))


@click.command(
    name="scratch_delete",
    help="Deletes a Salesforce DX Scratch Org leaving the config in the keychain for regeneration",
)
@click.argument("org_name")
@pass_config
def org_scratch_delete(config, org_name):
    org_config = config.keychain.get_org(org_name)
    if not org_config.scratch:
        raise click.UsageError("Org {} is not a scratch org".format(org_name))

    try:
        org_config.delete_org()
    except ScratchOrgException as e:
        raise click.UsageError(str(e))

    config.keychain.set_org(org_config)


org.add_command(org_browser)
org.add_command(org_connect)
org.add_command(org_default)
org.add_command(org_import)
org.add_command(org_info)
org.add_command(org_list)
org.add_command(org_remove)
org.add_command(org_scratch)
org.add_command(org_scratch_delete)


# Commands for group: task


@click.command(name="list", help="List available tasks for the current context")
@pass_config(load_keychain=False)
def task_list(config):
    data = []
    headers = ["task", "description"]
    task_groups = OrderedDict()
    for task in config.project_config.list_tasks():
        group = task["group"] or "Other"
        if group not in task_groups:
            task_groups[group] = []
        task_groups[group].append(task)
    for group, tasks in task_groups.items():
        data.append(("", ""))
        data.append(("-- {} --".format(group), ""))
        for task in sorted(tasks, key=operator.itemgetter("name")):
            data.append((task["name"], task["description"]))
    table = Table(data, headers)
    click.echo(table)
    click.echo("")
    click.echo(
        "Use "
        + click.style("cci task info <task_name>", bold=True)
        + " to get more information about a task."
    )


@click.command(name="doc", help="Exports RST format documentation for all tasks")
@pass_config(load_keychain=False)
def task_doc(config):
    config_src = config.global_config

    for name, options in list(config_src.tasks.items()):
        task_config = TaskConfig(options)
        doc = doc_task(name, task_config)
        click.echo(doc)
        click.echo("")


@click.command(name="info", help="Displays information for a task")
@click.argument("task_name")
@pass_config(load_keychain=False)
def task_info(config, task_name):
    task_config = config.project_config.get_task(task_name)
    doc = doc_task(task_name, task_config).encode()
    click.echo(rst2ansi(doc))


@click.command(name="run", help="Runs a task")
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
@pass_config
def task_run(config, task_name, org, o, debug, debug_before, debug_after, no_prompt):

    # Get necessary configs
    org, org_config = config.get_org(org, fail_if_missing=False)
    task_config = getattr(config.project_config, "tasks__{}".format(task_name))
    if not task_config:
        raise TaskNotFoundError("Task not found: {}".format(task_name))

    # Get the class to look up options
    class_path = task_config.get("class_path")
    task_class = import_class(class_path)

    # Parse command line options and add to task config
    if o:
        if "options" not in task_config:
            task_config["options"] = {}
        for name, value in o:
            # Validate the option
            if name not in task_class.task_options:
                raise click.UsageError(
                    'Option "{}" is not available for task {}'.format(name, task_name)
                )

            # Override the option in the task config
            task_config["options"][name] = value

    task_config = TaskConfig(task_config)

    # Create and run the task
    try:
        task = task_class(config.project_config, task_config, org_config=org_config)

        if debug_before:
            import pdb

            pdb.set_trace()

        task()

        if debug_after:
            import pdb

            pdb.set_trace()

    except CumulusCIUsageError as e:
        # Usage error; report with usage line and no traceback
        exception = click.UsageError(str(e))
        handle_exception_debug(config, debug, throw_exception=exception)
    except (CumulusCIFailure, ScratchOrgException) as e:
        # Expected failure; report without traceback
        exception = click.ClickException(str(e) or e.__class__.__name__)
        handle_exception_debug(config, debug, throw_exception=exception)
    except Exception:
        # Unexpected exception; log to sentry and raise
        handle_exception_debug(config, debug, no_prompt=no_prompt)

    config.alert("Task complete: {}".format(task_name))


# Add the task commands to the task group
task.add_command(task_doc)
task.add_command(task_info)
task.add_command(task_list)
task.add_command(task_run)


# Commands for group: flow


@click.command(name="list", help="List available flows for the current context")
@pass_config(load_keychain=False)
def flow_list(config):
    data = []
    headers = ["flow", "description"]
    for flow in config.project_config.list_flows():
        data.append((flow["name"], flow["description"]))
    table = Table(data, headers)
    click.echo(table)
    click.echo("")
    click.echo(
        "Use "
        + click.style("cci flow info <task_name>", bold=True)
        + " to get more information about a flow."
    )


@click.command(name="info", help="Displays information for a flow")
@click.argument("flow_name")
@pass_config(load_keychain=False)
def flow_info(config, flow_name):
    flow = config.project_config.get_flow(flow_name)
    render_recursive(flow)


@click.command(name="run", help="Runs a flow")
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
@pass_config
def flow_run(config, flow_name, org, delete_org, debug, o, skip, no_prompt):

    # Get necessary configs
    org, org_config = config.get_org(org)

    if delete_org and not org_config.scratch:
        raise click.UsageError("--delete-org can only be used with a scratch org")

    flow_config = config.project_config.get_flow(flow_name)

    # Parse command line options and add to task config
    options = {}
    if o:
        for option in o:
            options[option[0]] = option[1]

    # Create the flow and handle initialization exceptions
    try:
        flow = BaseFlow(
            config.project_config,
            flow_config,
            org_config,
            options,
            skip,
            name=flow_name,
        )

        flow()
    except CumulusCIUsageError as e:
        exception = click.UsageError(str(e))
        handle_exception_debug(config, debug, throw_exception=exception)
    except (CumulusCIFailure, ScratchOrgException) as e:
        exception = click.ClickException("Failed: {}".format(e.__class__.__name__))
        handle_exception_debug(config, debug, throw_exception=exception)
    except Exception:
        handle_exception_debug(config, debug, no_prompt=no_prompt)

    # Delete the scratch org if --delete-org was set
    if delete_org:
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo(
                "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
            )
            click.echo(str(e))

    config.alert("Flow Complete: {}".format(flow_name))


flow.add_command(flow_list)
flow.add_command(flow_info)
flow.add_command(flow_run)
