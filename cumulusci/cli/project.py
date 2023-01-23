import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict

import click
from jinja2 import Environment, PackageLoader

import cumulusci
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.utils.git import current_branch

from .runtime import pass_runtime


@click.group(
    "project", help="Commands for interacting with project repository configurations"
)
def project():
    pass


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

    init_from_context(context, echo=True)


def init_from_context(context: Dict[str, object], echo: bool = False):
    # Prep jinja2 environment for rendering files
    env = Environment(
        loader=PackageLoader(
            "cumulusci", os.path.join("files", "templates", "project")
        ),
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=True,
    )

    # Render templates
    for name in ("dot-gitignore", "README.md", "cumulusci.yml"):
        template = env.get_template(name)
        file_path = Path(name.replace("dot-", "."))
        if not file_path.is_file():
            file_path.write_text(template.render(**context))
        elif echo:
            click.echo(
                click.style(
                    f"{name} already exists. As a reference, here is what would be placed in the file if it didn't already exist:",
                    fg="red",
                )
            )
            click.echo(click.style(template.render(**context) + "\n", fg="yellow"))

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

    org_dict = {
        "beta.json": {
            "org_name": "Beta Test Org",
            "edition": "Developer",
            "managed": True,
        },
        "dev.json": {"org_name": "Dev Org", "edition": "Developer", "managed": False},
        "feature.json": {
            "org_name": "Feature Test Org",
            "edition": "Developer",
            "managed": False,
        },
        "release.json": {
            "org_name": "Release Test Org",
            "edition": "Enterprise",
            "managed": True,
        },
    }

    template = env.get_template("scratch_def.json")
    for org_name, properties in org_dict.items():
        org_path = Path("orgs/" + org_name)
        if not org_path.is_file():
            org_path.write_text(
                template.render(
                    package_name=context["package_name"],
                    **properties,
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

    if echo:
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
@click.option(
    "--resolution-strategy",
    help="The resolution strategy to use. Defaults to production.",
    default="production",
)
@pass_runtime(require_keychain=True)
def project_dependencies(runtime, resolution_strategy):
    dependencies = get_static_dependencies(
        runtime.project_config,
        resolution_strategy=resolution_strategy,
    )
    for line in dependencies:
        click.echo(f"{line}")


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
