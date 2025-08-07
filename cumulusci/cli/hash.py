import click
import hashlib
import json
import os
from cumulusci.core.dependencies.resolvers import get_static_dependencies
from cumulusci.core.utils import process_list_arg
from cumulusci.core.github import set_github_output
from cumulusci.utils.hashing import hash_dict
from pydantic import BaseModel
from .runtime import pass_runtime


@click.group(
    "hash",
    help="Commands for hashing parts of the project's CumulusCI configuration and state",
)
def hash_group():
    pass


# Commands for group: hash


@hash_group.command(
    name="config",
    help="Hashes all or part of the project's merged CumulusCI configuration",
)
@pass_runtime(require_project=True, require_keychain=False)  # maybe not needed...
@click.option(
    "--locators",
    "locators",
    help="A comma separated list of CumulusCI config locators to specify the top level of config key(s) to hash. Example: project__package,flows__ci_beta",
)
def hash_config(
    runtime,
    locators,
):
    locators_str = "for {}".format(locators) if locators else ""
    locators = process_list_arg(locators)
    config = runtime.project_config.config
    if locators:
        config = {loc: runtime.project_config.lookup(loc) for loc in locators}
    config_hash = hash_dict(config)
    click.echo(f"Hash of CumulusCI Config{locators_str}:")
    click.echo(config_hash)
    output_name = "HASH_CONFIG"
    if locators:
        output_name + "__" + "__AND__".join(locators)
    set_github_output(output_name, config_hash)


@hash_group.command(
    name="flow",
    help="Hashes a flow's configuration, either dynamic or frozen as a flat list of static steps",
)
@pass_runtime(require_project=True, require_keychain=False)  # maybe not needed...
@click.argument("flow_name")
@click.option(
    "--freeze",
    is_flag=True,
    help="Freeze the flow configuration as a flat list of static steps",
)
def hash_flow(
    runtime,
    flow_name,
    freeze,
):
    flow = runtime.get_flow(flow_name)

    steps = flow.steps
    if freeze:
        steps = flow.freeze(org_config=None)
    config_hash = hash_dict(steps)
    click.echo(f"Hash of flow {flow_name}:")
    click.echo(config_hash)
    output_name = "HASH_FLOW__" + flow_name
    if freeze:
        output_name + "__FROZEN"
    set_github_output(output_name, config_hash)


@hash_group.command(
    name="dependencies",
    help="Resolve and hash the project's current dependencies",
)
@click.option(
    "--resolution-strategy",
    help="The resolution strategy to use. Defaults to production.",
    default="production",
)
@pass_runtime(require_keychain=True)
def hash_dependencies(runtime, resolution_strategy):
    resolved = get_static_dependencies(
        runtime.project_config,
        resolution_strategy=resolution_strategy,
    )
    dependencies = []
    for dependency in resolved:
        click.echo(dependency)
        dependencies.append(dependency.dict())

    deps_hash = hash_dict(dependencies)
    click.echo(f"Hash of CumulusCI Dependencies for {resolution_strategy}:")
    click.echo(deps_hash)
