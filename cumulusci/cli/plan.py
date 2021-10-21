import json

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable

from .runtime import pass_runtime


@click.group("plan", help="Commands for getting information about MetaDeploy plans")
def plan():
    pass


@plan.command(name="list")
@click.option(
    "--json", "print_json", is_flag=True, help="Return the list of plans in JSON format"
)
@pass_runtime(require_project=True, require_keychain=True)
def plan_list(runtime, print_json):
    """List available plans for the current context.

    If --json is specified, the data will be a list of plans where
    each plan is a dictionary with the following keys:
    name, group, title, slug, tier

    """

    plans = runtime.project_config.plans or {}

    def _sort_func(plan):
        """Used to sort first by tier (primary, secondary, additional)
        and then by name"""
        name, config = plan
        tier = config.get("tier", "primary")
        tiers = ("primary", "secondary", "additional")
        tier_index = tiers.index(tier) if tier in tiers else 99
        return f"{tier_index} {name}"

    columns = ["name", "title", "slug", "tier"]
    raw_data = [
        dict(name=plan_name, **{key: plan_config.get(key, "") for key in columns[1:]})
        for plan_name, plan_config in sorted(plans.items(), key=_sort_func)
    ]

    if print_json:
        click.echo(json.dumps(raw_data))
        return

    data = [[name.title() for name in columns]]
    data.extend([list(row.values()) for row in raw_data]
    console = Console()
    table = CliTable(data=data)
    console.print(table)
