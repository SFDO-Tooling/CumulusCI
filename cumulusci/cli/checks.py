import logging

import click

from cumulusci.cli.ui import CliTable
from cumulusci.core.config import FlowConfig
from cumulusci.core.flowrunner import PreflightFlowCoordinator

from .runtime import pass_runtime


@click.group(
    "checks",
    help="Commands for getting information about Preflight checks for a Radagast plan",
)
def checks():
    pass


@checks.command(name="info", help="Displays checks for a plan")
@click.argument("plan_name")
@pass_runtime(require_project=True)
def checks_info(runtime, plan_name):

    """
    Displays checks for a Radagast plan.
    """

    # Check if the plan exists or not
    plans = runtime.project_config.plans or {}
    if plan_name not in plans:
        raise click.UsageError(
            f"Unknown plan '{plan_name}'. To view available plans run: `cci plan list`"
        )

    # Get the checks under a plan
    preflight_checks = [
        [check.get("action", ""), check.get("message", ""), check.get("when", "")]
        for check in plans[plan_name].get("checks", [])
    ]
    # Create Cli Table to display the checks
    plan_preflight_checks_table = CliTable(
        title="Plan Preflights",
        data=[
            ["Action", "Message", "When"],
            *preflight_checks,
        ],
    )
    plan_preflight_checks_table.echo()


@checks.command(name="run", help="Runs checks under a plan")
@click.argument("plan_name")
@click.option(
    "--org",
    help="Specify the target org.  By default, runs against the current default org",
)
@pass_runtime(require_keychain=True, require_project=True)
def checks_run(runtime, plan_name, org):
    """
    Runs checks for a Radagast plan.
    """
    plans = runtime.project_config.plans or {}

    # Check if the plan exists or not
    if plan_name not in plans:
        raise click.UsageError(
            f"Unknown plan '{plan_name}'. To view available plans run: `cci plan list`"
        )

    logger = logging.getLogger("cumulusci.flows")
    org_logger = logging.getLogger("cumulusci.core.config.base_config")

    def _rule(fill="=", length=60, new_line=False):
        logger.info(f"{fill * length}")
        if new_line:
            logger.info("")

    org, org_config = runtime.get_org(org)

    # Print the org details
    _rule(fill="-", new_line=False)
    logger.info("Organization:")
    logger.info(f"  Username: {org_config.username}")
    logger.info(f"    Org Id: {org_config.org_id}")
    _rule(fill="-", new_line=True)
    logger.info(f"Running preflight checks for the plan {plan_name} ...")
    _rule(new_line=True)
    checks = plans[plan_name]["checks"]

    # Check if there are no checks available under the plan
    if checks.length == 0:
        raise click.UsageError(
            f"No checks exists for the '{plan_name}'. To view available checks run: `cci checks info`"
        )

    # Run the preflight checks under the plan
    flow_config = FlowConfig({"checks": checks, "steps": {}})
    flow_coordinator = PreflightFlowCoordinator(
        runtime.project_config,
        flow_config,
        name="preflight",
    )
    # Ignore the logs coming via the pre flight coordinator execution
    logger.setLevel(logging.WARNING)
    org_logger.setLevel(logging.WARNING)
    flow_coordinator.run(org_config)
    logger.setLevel(logging.INFO)
    org_logger.setLevel(logging.INFO)
    results = flow_coordinator.preflight_results

    # Check if the there are any errors/warnings while running checks
    if results:
        raise_error = False
        print(results.items())
        for step_name, step_results in results.items():
            table_header_row = ["Status", "Message"]
            table_data = [table_header_row]

            for result in step_results:
                table_data.append([result["status"], result["message"]])
                if result["status"] == "error":
                    raise_error = True
            table = CliTable(
                table_data,
            )
            table.echo(plain=True)
        if raise_error:
            # Raise an exception if there are any failed pre flight checks
            raise Exception(
                "Some of the checks failed with errors. Please check the logs for details."
            )
        else:
            logger.info("The preflight checks ran succesfully with the warnings.")
    else:
        logger.info("The preflight checks ran succesfully.")
