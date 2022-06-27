import json

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable
from cumulusci.core.metadeploy.plans import get_frozen_steps
from cumulusci.utils.yaml.cumulusci_yml import Plan

from .runtime import pass_runtime


@click.group("plan", help="Commands for getting information about MetaDeploy plans")
def plan():
    pass  # pragma: no cover


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
        tiers = Plan.schema()["properties"]["tier"]["enum"]
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
    data.extend([list(row.values()) for row in raw_data])
    console = Console()
    table = CliTable(data=data)
    console.print(table)

    click.echo(
        "Use "
        + click.style("cci plan info <plan_name>", bold=True)
        + " to get more information about a task."
    )


@plan.command(name="info")
@click.argument("plan_name")
@click.option(
    "--messages", "messages_only", is_flag=True, help="Show only plan messages"
)
@pass_runtime(require_project=True, require_keychain=True)
def plan_info(runtime, plan_name, messages_only):
    """
    Displays information for a MetaDeploy plan.
    """

    plans = runtime.project_config.plans or {}

    if plan_name not in plans:
        raise click.UsageError(
            f"Unknown plan '{plan_name}'. To view available plans run: `cci plan list`"
        )

    plan_config = plans[plan_name]

    console = Console()

    raw_data = {
        "title": plan_config["title"],
        "yaml_key": plan_name,
        "slug": plan_config["slug"],
        "tier": plan_config["tier"],
        "hidden": not plan_config.get("is_listed", "False"),
        "preflight_message": plan_config.get("preflight_message", ""),
        "post_install_message": plan_config.get("post_install_message", ""),
        "error_message": plan_config.get("error_message", ""),
        "checks": [
            [check.get("action", ""), check.get("message", ""), check.get("when", "")]
            for check in plan_config.get("checks", [])
        ],
        "steps": {},  # expensive to compute so we'll do later
    }

    messages_table = CliTable(
        title="Messages",
        data=[
            ["Type", "Message"],
            ["Title", raw_data["title"]],
            ["Preflight", raw_data["preflight_message"]],
            ["Post-install", raw_data["post_install_message"]],
            ["Error", raw_data["error_message"]],
        ],
    )

    if messages_only:
        console.print(messages_table)
        return

    config_table = CliTable(
        title="Config",
        data=[
            ["Key", "Value"],
            ["YAML Key", raw_data["yaml_key"]],
            ["Slug", raw_data["slug"]],
            ["Tier", raw_data["tier"]],
            ["Hidden?", raw_data["hidden"]],
        ],
    )

    plan_preflight_checks_table = CliTable(
        title="Plan Preflights",
        data=[
            ["Action", "Message", "When"],
            *raw_data["checks"],
        ],
    )

    steps = get_frozen_steps(runtime.project_config, plan_config)
    raw_data["steps"] = [
        [
            step_n + 1,
            step["name"],
            step["is_required"],
            step.get("is_recommended", True),
        ]
        for step_n, step in enumerate(steps)
    ]
    raw_data["steps_preflight_checks"] = [
        [
            step_n + 1,
            check.get("action", ""),
            check.get("message", ""),
            check.get("when", ""),
        ]
        for step_n, step in enumerate(steps)
        for check in step["task_config"]["checks"]
    ]

    step_preflight_checks_table = CliTable(
        title="Step Preflights",
        data=[
            ["Step", "Action", "Message", "When"],
            *raw_data["steps_preflight_checks"],
        ],
    )

    CliTable.PICTOGRAM_TRUE = "Yes"
    CliTable.PICTOGRAM_FALSE = "No"
    steps_table = CliTable(
        title="Steps",
        data=[
            ["Step", "Name", "Required", "Recommended"],
            *raw_data["steps"],
        ],
    )

    console.print(config_table)
    console.print(messages_table)
    console.print(plan_preflight_checks_table)
    console.print(step_preflight_checks_table)
    console.print(steps_table)
