import json

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable

from .runtime import pass_runtime


@click.group("plan", help="Commands for getting information about MetaDeploy plans")
def plan():
    pass


@plan.command(name="list")
@click.option("--verbose", "verbose", is_flag=True, help="Verbose mode")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=True, require_keychain=True)
def plan_list(runtime, print_json, verbose):
    """List available plans for the current context."""

    # when there are no plans, `project_config.plans` is an empty
    # list rather than empty dictionary. I don't know why that is,
    # but I need it to be an empty dictionary.
    plans = runtime.project_config.plans or {}
    columns = {"title": "Title", "slug": "Plan Slug", "tier": "Tier"}
    if verbose:
        columns.update(
            {
                "error_message": "Error Message",
                "post_install_message": "Post-install Message",
                "preflight_message": "PreFlight Message",
            }
        )

    data = {
        plan_name: {key: plan_config.get(key, "") for key in columns.keys()}
        for plan_name, plan_config in plans.items()
        for plan in plans
    }

    data = {}
    for plan_name, plan_config in plans.items():
        data[plan_name] = {key: plan_config.get(key, "") for key in columns.keys()}

    if print_json:
        click.echo(json.dumps(data))

    else:
        rows = [["Name"] + list(columns.values())]
        for plan_name, plan_config in plans.items():
            row = [plan_name]
            row.extend([plan_config.get(key, "") for key in columns.keys()])
            rows.append(row)
        table = CliTable(title="MetaDeploy Plans", data=rows)
        console = Console()
        console.print(table, markup=False)
