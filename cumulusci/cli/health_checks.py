from cumulusci.cli.cci import cci
from cumulusci.core.config import OrgConfig, BaseProjectConfig
from cumulusci.core.exceptions import CumulusCIException
from cumulusci.core.runtime import BaseCumulusCI
import click

@click.group(name="health_checks", help="Health checks on the target Salesforce org.")
def health_checks():
    pass

def get_org_config(org_name):
    runtime = BaseCumulusCI(BaseProjectConfig())
    org_name = org_name or runtime.keychain.get_default_org()[0] ided
    org_config = runtime.keychain.get_org(org_name)
    org_config.refresh_oauth_token(None)
    return org_config

@health_checks.command(name="settings", help="Check if specified org settings are enabled.")
@click.option('--org', help="The org to run the health checks against")
@click.option('--settings', multiple=True, help="List of org settings to check")
@click.option('--halt-on-failure', is_flag=True, help="Halt execution on error")
def check_settings(org, settings, halt_on_failure):
    org_config = get_org_config(org)
    click.echo(f"Running settings health check on org: {org_config.name}")

    failures = []
    try:
        settings_data = org_config.salesforce_client.restful("services/data/v54.0/sobjects/Organization/Settings")
        for setting in settings:
            if not settings_data.get(setting, False):
                click.echo(f"❌ {setting} is NOT enabled.")
                failures.append(setting)
            else:
                click.echo(f"✅ {setting} is enabled.")
    except Exception as e:
        click.echo(f"Error checking settings: {e}")
        failures.extend(settings)
    
    handle_failures(failures, halt_on_failure)

@health_checks.command(name="permsets", help="Check if specified permission sets are assigned")
@click.option('--org', help="The org to run the health checks against.")
@click.option('--permsets', multiple=True, help="List of permission sets to check")
@click.option('--halt-on-failure', is_flag=True, help="Halt execution on error")
def check_permsets(org, permsets, halt_on_failure):
    org_config = get_org_config(org)
    click.echo(f"Running permission set health check on org: {org_config.name}")

    failures = []
    current_user_id = org_config.userinfo.get('user_id')

    try:
        result = org_config.salesforce_client.query(
            f"SELECT PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId = '{current_user_id}'"
        )
        assigned_permsets = [permset['PermissionSet']['Name'] for permset in result.get('records', [])]
        for permset in permsets:
            if permset not in assigned_permsets:
                click.echo(f"❌ Permission Set {permset} is NOT assigned to the current user.")
                failures.append(permset)
            else:
                click.echo(f"✅ Permission Set {permset} is assigned to the current user.")
    except Exception as e:
        click.echo(f"Error checking permission sets: {e}")
        failures.extend(permsets)

    handle_failures(failures, halt_on_failure)

@health_checks.command(name="licenses", help="Check if specified permission set licenses are assigned")
@click.option('--org', help="The org to run the health checks against")
@click.option('--permset-licenses', multiple=True, help="List of permission set licenses to check")
@click.option('--halt-on-failure', is_flag=True, help="Halt execution on error")
def check_permset_licenses(org, permset_licenses, halt_on_failure):
    org_config = get_org_config(org)
    click.echo(f"Running permission set license health check on org: {org_config.name}")

    failures = []
    current_user_id = org_config.userinfo.get('user_id')

    try:
        result = org_config.salesforce_client.query(
            f"SELECT PermissionSetLicense.DeveloperName FROM PermissionSetLicenseAssignment WHERE AssigneeId = '{current_user_id}'"
        )
        assigned_licenses = [license['PermissionSetLicense']['DeveloperName'] for license in result.get('records', [])]
        for license in permset_licenses:
            if license not in assigned_licenses:
                click.echo(f"❌ Permission Set License {license} is NOT assigned to the current user.")
                failures.append(license)
            else:
                click.echo(f"✅ Permission Set License {license} is assigned to the current user.")
    except Exception as e:
        click.echo(f"Error checking permission set licenses: {e}")
        failures.extend(permset_licenses)

    handle_failures(failures, halt_on_failure)

def handle_failures(failures, halt_on_failure):
    if failures:
        click.echo(f"\nThe following checks failed: {', '.join(failures)}")
        if halt_on_failure:
            raise CumulusCIException("Configurations are missed")
    else:
        click.echo("All checks passed.")
