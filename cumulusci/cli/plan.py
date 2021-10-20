import json
from collections import defaultdict

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable

from .runtime import pass_runtime

DEFAULT_GROUP = "Uncategorized Plans"


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

    columns = ["name", "group", "title", "slug", "tier"]
    raw_data = [
        dict(name=plan_name, **{key: plan_config.get(key, "") for key in columns[1:]})
        for plan_name, plan_config in sorted(plans.items(), key=_sort_func)
    ]

    if print_json:
        click.echo(json.dumps(raw_data))

    else:
        # start each group by adding a row of column headers,
        # then pull the values from the dictionaries for each row
        columns.remove("group")
        groups = defaultdict(
            lambda: [[column.title() for column in columns]],
        )

        for row in raw_data:
            group_name = (row.pop("group") or DEFAULT_GROUP).title()
            groups[group_name].append(list(row.values()))

        if not groups:
            # as per a discussion, we'll force a single empty table if
            # there are no plans so that the output is consistent with
            # when we have plans. Referencing the group will trigger
            # the creationg of the default value with column headers
            groups[DEFAULT_GROUP]

        console = Console()
        for group_name, group_data in sorted(groups.items()):
            table = CliTable(title=group_name, data=group_data)
            console.print(table)
