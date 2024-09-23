import json
from datetime import datetime, timedelta

import click
from rich.console import Console
from rich.text import Text
from rich.table import Table

from cumulusci.cli.org import orgname_option_or_argument
from cumulusci.core.config.org_history import OrgActionStatus
from cumulusci.core.utils import format_duration
from cumulusci.utils import parse_api_datetime
from cumulusci.utils.yaml.render import dump_yaml

from .runtime import pass_runtime


@click.group("history", help="Commands for interacting with org history")
def history():
    pass


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
@click.option("--json", "print_json", is_flag=True, help="Print as JSON.")
@click.option("--indent", type=int, help="Indentation level for JSON output.")
@pass_runtime(require_project=False, require_keychain=True)
def org_history_list(
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
    print_json=False,
    indent=4,
):
    org_name, org_config = runtime.get_org(org_name)
    if print_json:
        click.echo(json.dumps(org_config.history.dict(), indent=indent))
        return

    console = Console()
    table = Table(title="Org History", show_lines=True)
    table.add_column("Hash")
    table.add_column("Type")
    table.add_column("Time")
    table.add_column("Status")
    table.add_column("Details")

    filters = {
        "action_type": action_type,
        "status": status,
        "action_hash": action_hash,
        "config_hash": config_hash,
        "exclude_action_hash": exclude_action_hash,
        "exclude_config_hash": exclude_config_hash,
        "before": before,
        "after": after,
    }

    for action in org_config.history.filtered_actions(**filters):
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

    if not org_config.history.actions:
        table.add_row("No history available", "", "", "", "")
    console.print(table)


@history.command(name="info", help="Display information for a specific action hash")
@click.argument("hash")
@orgname_option_or_argument(required=False)
@click.option("--json", "print_json", is_flag=True, help="Print as JSON.")
@click.option("--indent", type=int, help="Indentation level for JSON output.")
@pass_runtime(require_project=False, require_keychain=True)
def org_history_info(runtime, org_name, hash, print_json, indent):
    org_name, org_config = runtime.get_org(org_name)
    action = org_config.history.get_action_by_hash(hash)
    if print_json:
        click.echo(json.dumps(action.dict(), indent=indent))
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
    table = Table(title=f"Org History: {hash}")
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


@history.command(name="clear", help="Clear the org history")
@orgname_option_or_argument(required=False)
@click.option("--all", is_flag=True, help="Clear all history for the org.")
@click.option("--before", help="Clear history before the specified date.")
@click.option("--after", help="Clear history after the specified date.")
@click.option("--hash", help="Clear a specific action hash from the history.")
@pass_runtime(require_project=False, require_keychain=True)
def org_history_clear(runtime, org_name, all, before, after, hash):
    org_name, org_config = runtime.get_org(org_name)
    if all:
        org_config.clear_history()
        click.echo("All history cleared.")
        return
    elif before:
        org_config.clear_history(before=parse_api_datetime(before))
        click.echo(f"History cleared before {before}.")
    elif after:
        org_config.clear_history(after=parse_api_datetime(after))
        click.echo(f"History cleared after {after}.")
    elif hash:
        org_config.clear_history(hash=hash)
        click.echo(f"History cleared for action {hash}.")
    else:
        click.echo("Please specify --before, --after, or --all")


@history.command(name="enable", help="Enable history tracking for the org")
@orgname_option_or_argument(required=False)
@pass_runtime(require_project=False, require_keychain=True)
def org_history_enable(runtime, org_name):
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
def org_history_disable(runtime, org_name):
    org_name, org_config = runtime.get_org(org_name)
    if not org_config.track_history:
        click.echo("Org history tracking is already disabled for this org.")
        return
    org_config.track_history = False
    org_config.save()
    click.echo("Org history tracking disabled.")
