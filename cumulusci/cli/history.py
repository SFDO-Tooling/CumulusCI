import json
from datetime import datetime, timedelta
from dateutil.parser import parse

import click
from rich.console import Console
from rich.text import Text
from rich.table import Table

from cumulusci.cli.org import orgname_option_or_argument
from cumulusci.core.org_history import (
    FilterOrgActions,
    OrgActionStatus,
)
from cumulusci.core.utils import format_duration
from cumulusci.core.flowrunner import flow_from_org_actions
from cumulusci.utils.hashing import dump_json
from cumulusci.utils.yaml.render import dump_yaml

from .runtime import pass_runtime


def color_by_status(name, status, text=None):
    color = "green" if status == OrgActionStatus.SUCCESS.value else "red"
    if status == OrgActionStatus.FAILURE.value:
        color = "orange"
    style = f"bold {color}"
    if text:
        text.append(name, style=style)
        return text
    return Text(name, style=style)


def instance_from_locals(model, data: dict):
    """Create an instance of a model from a dictionary of data using only keys matching fields for the model."""
    model_data = {}
    for field in model.__fields__.keys():
        if field in data:
            model_data[field] = data[field]

    return model.parse_obj(model_data)


@click.group("history", help="Commands for interacting with org history")
def history():
    pass


@history.command(
    name="previous",
    help="List the previous org instances for this org and a summary of their history.",
)
@orgname_option_or_argument(required=False)
@click.option("--json", "print_json", is_flag=True, help="Print as JSON.")
@click.option("--indent", type=int, help="Indentation level for JSON output.")
@pass_runtime(require_project=True, require_keychain=True)
def history_previous(runtime, org_name, print_json, indent):
    org_name, org_config = runtime.get_org(org_name)
    previous_orgs = org_config.history.previous_orgs
    if print_json:
        click.echo(
            dump_json(
                previous_orgs,
                indent=indent,
            )
        )
        return

    console = Console()
    table = Table(
        title=f"Previous Orgs ({org_name})",
        show_lines=True,
        title_justify="left",
    )
    table.add_column("Org Id")
    table.add_column("Config Hash")
    table.add_column("Created")
    table.add_column("# Actions")
    table.add_column("Tasks & Flows")

    last_org_id = None
    if not previous_orgs:
        table.add_row("No previous orgs available", "", "", "", "")
    else:
        for org_id, org in previous_orgs.items():
            last_org_id = org_id
            created = org.filtered_actions(FilterOrgActions(action_type=["OrgCreate"]))
            if created:
                date = datetime.fromtimestamp(created[0].timestamp)
                created = Text(date.strftime("%Y-%m-%d\n%H:%M:%S"))
            else:
                created = Text("N/A")
            tasks_and_flows = Text()
            for action in org.filtered_actions(
                FilterOrgActions(action_type=["Task", "Flow"])
            ):
                tasks_and_flows = color_by_status(
                    name=action.name,
                    status=action.status,
                    text=tasks_and_flows,
                )

            table.add_row(
                Text(org_id, style="bold"),
                org.hash_config,
                created,
                str(len(org.actions)),
                tasks_and_flows,
            )

    console.print()
    console.print(table)
    console.print()

    console.print(
        Text("Use the Org Id to list history for a previous org:", style="gray")
    )
    console.print()
    console.print(
        Text(f"    cci history list --org-id {last_org_id or '<org_id>'}", style="bold")
    )
    console.print()


@history.command(name="list", help="List the orgs history")
@orgname_option_or_argument(required=False)
@click.option(
    "--action-type", help="Filter by action types using comma separated names."
)
@click.option(
    "--status",
    help="Filter by status using comma separated names. Options: success, failure, error",
)
@click.option(
    "--action-hash",
    help="Limit results to specific action hashes, separated by commas, then filtered by other options.",
)
@click.option(
    "--config-hash",
    help="Limit results to specific config hashes, separated by commas, then filtered by other options.",
)
@click.option(
    "--exclude-action-hash",
    help="Exclude specific action hashes, separated by commas.",
)
@click.option(
    "--exclude-config-hash",
    help="Exclude specific config hashes, separated by commas.",
)
@click.option(
    "--before", help="Include only actions that ran before the specified action hash"
)
@click.option(
    "--after", help="Include only actions that ran after the specified action hash"
)
@click.option(
    "--org-id",
    help="List the actions run against a previous org instance by org id. Use `cci history previous` to list previous org instances.",
)
@click.option("--json", "print_json", is_flag=True, help="Print as JSON.")
@click.option("--indent", type=int, help="Indentation level for JSON output.")
@pass_runtime(require_project=True, require_keychain=True)
def history_list(
    runtime,
    org_name=None,
    action_type=None,
    status=None,
    action_hash=None,
    config_hash=None,
    exclude_action_hash=None,
    exclude_config_hash=None,
    before=None,
    after=None,
    org_id=None,
    print_json=False,
    indent=4,
):
    org_name, org_config = runtime.get_org(org_name)

    org_history = org_config.history

    if org_config.track_history is False:
        click.echo("Org history tracking is disabled for this org.")
        click.echo(
            "*Use `cci org history enable` to enable history tracking for this org.*"
        )
        if org_history and (org_history.actions or org_history.previous_orgs):
            click.echo(
                "Org history found from before tracking was disabled. Continuing..."
            )
        return

    if org_id:
        org_history = org_history.previous_orgs.get(org_id)

    if print_json:
        click.echo(dump_json(org_history.dict(), indent=indent))
        return

    console = Console()
    console.print()
    table_title = f"Org History for {org_name}"
    if org_id:
        table_title += f" (Previous Org: {org_id})"
    else:
        table_title += f" ({org_config.org_id})"
    table = Table(
        title=table_title,
        show_lines=True,
        title_justify="left",
    )
    table.add_column("Hash")
    table.add_column("Type")
    table.add_column("Time")
    table.add_column("Status")
    table.add_column("Details")

    filters = instance_from_locals(FilterOrgActions, locals())

    actions = org_history.filtered_actions(filters)
    if not actions:
        table.add_row("No history available", "", "", "", "")

    else:
        last_action_hash = None
        for action in org_history.filtered_actions(filters):
            color = "green" if action.status == OrgActionStatus.SUCCESS.value else "red"
            if action.status == OrgActionStatus.FAILURE.value:
                color = "orange"
            status_text = Text(str(action.status), style=f"bold {color}")
            table.add_row(
                str(action.column_hash),
                str(action.column_type),
                str(action.column_date),
                status_text,  # Add Text object directly
                str(action.column_details),
            )
            last_action_hash = action.hash_action

    console.print(table)
    console.print()
    if last_action_hash:
        console.print(
            Text(
                "Use the Action Hash to get the info on an action, for example:",
                style="",
            )
        )
        console.print()
        console.print(Text(f"   cci history info {last_action_hash}", style="bold"))
    console.print()


@history.command(name="info", help="Display information for a specific action hash")
@click.argument("action_hash")
@orgname_option_or_argument(required=False)
@click.option("--json", "print_json", is_flag=True, help="Print as JSON.")
@click.option("--indent", type=int, help="Indentation level for JSON output.")
@click.option(
    "--org-id",
    help="Lookup the action in the history of a previous org instance by org id.",
)
@pass_runtime(require_project=True, require_keychain=True)
def history_info(runtime, org_name, action_hash, print_json, indent, org_id):
    org_name, org_config = runtime.get_org(org_name)

    org_history = org_config.history
    if org_id:
        org_history = org_config.history.previous_orgs.get(org_id)

    action = org_history.get_action_by_hash(action_hash)
    if print_json:
        click.echo(dump_json(action.dict(), indent=indent))
        return

    timestamp = None

    def process_value(key, value):
        if key == "timestamp":
            timestamp = datetime.fromtimestamp(value)
            value = timestamp.strftime("%Y-%m-%d %H:%M:%S")
        elif key == "duration":
            value = format_duration(timedelta(seconds=value))
        elif isinstance(value, dict):
            value = dump_yaml(value, indent=indent)
        elif isinstance(value, list):
            value = dump_yaml(value, indent=indent)
        return str(value)

    console = Console()
    table = Table(title=f"Org History: {action_hash}")
    table.add_column("Key")
    table.add_column("Value")

    action_info = action.dict()
    pop_first = [
        "action_type",
        "name",
        "description",
        "group",
        "status",
        "timestamp",
        "duration",
    ]
    for key in pop_first:
        if key in action_info:

            table.add_row(key, process_value(key, action_info.pop(key)))
    if "description" in action_info:
        action_info["details"] = action_info.pop("description")

    for key, value in action_info.items():
        table.add_row(key, process_value(key, value))

    console.print(table)


@history.command(name="replay", help="List the orgs history")
@orgname_option_or_argument(required=False)
@click.option(
    "--action-type",
    help="Filter by action types using comma separated names. Can be None, Task Flow or Flow,Task",
)
@click.option(
    "--status",
    help="Filter by status using comma separated names. Options: success, failure, error",
)
@click.option(
    "--action-hash",
    help="Limit results to specific action hashes, separated by commas, then filtered by other options.",
)
@click.option(
    "--config-hash",
    help="Limit results to specific config hashes, separated by commas, then filtered by other options.",
)
@click.option(
    "--exclude-action-hash",
    help="Exclude specific action hashes, separated by commas.",
)
@click.option(
    "--exclude-config-hash",
    help="Exclude specific config hashes, separated by commas.",
)
@click.option(
    "--before", help="Include only actions that ran before the specified action hash"
)
@click.option(
    "--after", help="Include only actions that ran after the specified action hash"
)
@click.option("--no-prompts", is_flag=True, help="Skip all prompts")
@click.option("--dry-run", is_flag=True, help="Dry run the flow")
@pass_runtime(require_project=True, require_keychain=True)
def history_replay(
    runtime,
    org_name=None,
    action_type=None,
    status=None,
    action_hash=None,
    config_hash=None,
    exclude_action_hash=None,
    exclude_config_hash=None,
    before=None,
    after=None,
    no_prompts=False,
    dry_run=False,
):
    org_name, org_config = runtime.get_org(org_name)

    if status:
        status = status.split(",")
        for value in status:
            if value not in ("success", "failure", "error"):
                raise click.UsageError(
                    "Invalid value for --status. Must be one of: success, failure, error"
                )

    actions = org_config.history.filtered_actions(
        action_type=action_type,
        status=status,
        action_hash=action_hash,
        config_hash=config_hash,
        exclude_action_hash=exclude_action_hash,
        exclude_config_hash=exclude_config_hash,
        before=before,
        after=after,
    )

    flow = flow_from_org_actions(
        name="replay__org__{org_name}",
        description="Replay of org actions",
        group="Replay",
        project_config=runtime.project_config,
        org_actions=actions,
    )

    click.echo(f"Please review the follow constructed flow for approval:")
    for step in flow.steps:
        click.echo(f"[{step.step_num}] {step.task_name}:{step.task_class}")
        click.echo(f"  from: {step.path}")
        if step.task_config["options"]:
            click.echo(f"  options:")
            click.echo(
                "    "
                + "    ".join(dump_yaml(step.task_config["options"]).splitlines(True))
            )
        click.echo()
    click.echo(flow.get_summary())

    if dry_run:
        return
    elif not no_prompts:
        click.confirm("Would you like to run this flow?", abort=True)
    else:
        click.echo("Running flow...")
    result = flow.run(org_config)
    org_config.add_action_to_history(flow.action)


@history.command(name="clear", help="Clear the org history")
@orgname_option_or_argument(required=False)
@click.option("--clear-all", is_flag=True, help="Clear all history for the org.")
@click.option("--before", help="Clear history before the specified action hash.")
@click.option("--after", help="Clear history after the specified action hash.")
@click.option("--action-hash", help="Clear a specific action hash from the history.")
@click.option(
    "--org-id", help="Clear the history for a previous org instance by org id."
)
@pass_runtime(require_project=False, require_keychain=True)
def history_clear(runtime, org_name, clear_all, before, after, action_hash, org_id):
    org_name, org_config = runtime.get_org(org_name)
    console = Console()
    console.print()
    if clear_all:
        org_config.clear_history(org_id=org_id)
    elif any([before, after, action_hash]):
        filters = FilterOrgActions(
            action_hash=action_hash,
            before=before,
            after=after,
        )

        console.print(Text("Using filters:", style="bold"))
        console.print(
            dump_yaml(
                {k: v for k, v in filters.dict().items() if v is not None}, indent=4
            )
        )
        console.print()
        if org_id:
            history = org_config.history.lookup_org(org_id)
        else:
            history = org_config.history
        actions = history.filtered_actions(
            filters=filters,
        )

        console.print()
        if not actions:
            console.print(Text("No actions found to clear.", style="bold yellow"))
            console.print()
            return

        table = Table(title=f"Matched {len(actions)} Actions to be cleared")

        table.add_column("Action Hash")
        table.add_column("Type")
        table.add_column("Time")
        table.add_column("Status")

        for action in actions:
            table.add_row(
                action.hash_action,
                action.column_type,
                action.column_date,
                action.column_status,
            )
        console.print(table)
        console.print()
        if not click.confirm("Are you sure you want to clear these actions?"):
            return

        org_config.clear_history(
            filters=filters,
            org_id=org_id,
        )
    else:
        click.echo("Please specify --before, --after, or --all")


@history.command(name="enable", help="Enable history tracking for the org")
@orgname_option_or_argument(required=False)
@pass_runtime(require_project=False, require_keychain=True)
def history_enable(runtime, org_name):

    org_name, org_config = runtime.get_org(org_name)
    if org_config.track_history:
        click.echo("Org history tracking is already enabled for this org.")
        return
    org_config.track_history = True
    org_config.save()
    click.echo("Org history tracking enabled.")


@history.command(name="disable", help="Disable history tracking for the org")
@orgname_option_or_argument(required=False)
@pass_runtime(require_project=False, require_keychain=True)
def history_disable(runtime, org_name):
    org_name, org_config = runtime.get_org(org_name)
    if not org_config.track_history:
        click.echo("Org history tracking is already disabled for this org.")
        return
    org_config.track_history = False
    org_config.save()
    click.echo("Org history tracking disabled.")
