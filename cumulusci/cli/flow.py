import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import click

from cumulusci.core.exceptions import FlowNotFoundError
from cumulusci.core.utils import format_duration
from cumulusci.utils import document_flow, flow_ref_title_and_intro
from cumulusci.utils.yaml.safer_loader import load_yaml_data

from .runtime import pass_runtime
from .ui import CliTable
from .utils import group_items


@click.group("flow", help="Commands for finding and running flows for a project")
def flow():
    pass


@flow.command(name="doc", help="Exports RST format documentation for all flows")
@click.option(
    "--project", "project", is_flag=True, help="Include project-specific flows only"
)
@pass_runtime(require_project=False, require_keychain=True)
def flow_doc(runtime, project=False):
    flow_info_path = Path(__file__, "..", "..", "..", "docs", "flows.yml").resolve()
    with open(flow_info_path, "r", encoding="utf-8") as f:
        flow_info = load_yaml_data(f)
    click.echo(flow_ref_title_and_intro(flow_info["intro_blurb"]))
    flow_info_groups = list(flow_info["groups"].keys())

    universal_flows = runtime.universal_config.list_flows()
    if project:
        flows = [
            flow
            for flow in runtime.project_config.list_flows()
            if flow not in universal_flows
        ]
    else:
        flows = universal_flows
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
        table = CliTable(
            data,
            group,
        )
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
        output = coordinator.get_summary(verbose=True)
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
    "--no-prompt",
    is_flag=True,
    help="Disables all prompts.  Set for non-interactive mode use such as calling from scripts or CI systems",
)
@pass_runtime(require_keychain=True)
def flow_run(runtime, flow_name, org, delete_org, debug, o, no_prompt):

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
    except Exception:
        runtime.alert(f"Flow error: {flow_name}")
        raise
    finally:
        # Delete the scratch org if --delete-org was set
        if delete_org:
            try:
                org_config.delete_org()
            except Exception as e:
                click.echo(
                    "Scratch org deletion failed.  Ignoring the error below to complete the flow:"
                )
                click.echo(str(e))

    runtime.alert(f"Flow Complete: {flow_name}")
