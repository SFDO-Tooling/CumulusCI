import json

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable

from .runtime import pass_runtime


@click.group("plan", help="Commands for getting information about metadeploy plans")
def plan():
    pass


@plan.command(name="list", help="List available plans for the current context")
@click.option("--verbose", "verbose", is_flag=True, help="Verbose mode")
@click.option("--json", "print_json", is_flag=True, help="Print a json string")
@pass_runtime(require_project=True, require_keychain=True)
def plan_list(runtime, print_json, verbose):
    plans = runtime.project_config.plans
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
