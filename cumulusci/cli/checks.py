import click

from .runtime import pass_runtime


@click.group("checks", help="Commands for running preflight checks for a plan")
def checks():
    pass


@checks.command(name="info", help="Displays preflight checks for a plan")
@click.argument("plan_name")
@pass_runtime(require_project=True)
def checks_info(runtime, plan_name):
    click.echo("This plan has the following preflight checks: ")


@checks.command(name="run", help="Runs checks under a plan")
@click.argument("plan_name")
@click.option(
    "--org",
    help="Specify the target org.  By default, runs against the current default org",
)
@pass_runtime(require_keychain=True, require_project=True)
def checks_run(runtime, plan_name, org):

    # Get necessary configs
    org, org_config = runtime.get_org(org)
    m = "Running checks for the plan " + plan_name
    click.echo(m)
