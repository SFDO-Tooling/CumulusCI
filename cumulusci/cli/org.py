import code
import json
import runpy
import webbrowser
from datetime import datetime
from urllib.parse import urlencode, urlparse

import click
from rich.console import Console

from cumulusci.cli.ui import CliTable, SimpleSalesforceUIHelpers
from cumulusci.core.config import OrgConfig, ScratchOrgConfig
from cumulusci.core.config.sfdx_org_config import SfdxOrgConfig
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.oauth.client import (
    PROD_LOGIN_URL,
    SANDBOX_LOGIN_URL,
    OAuth2Client,
    OAuth2ClientConfig,
)
from cumulusci.salesforce_api.utils import get_simple_salesforce_connection
from cumulusci.utils import parse_api_datetime

from .runtime import CliRuntime, pass_runtime


@click.group("org", help="Commands for connecting and interacting with Salesforce orgs")
def org():
    pass


def set_org_name(required):
    """Generate a callback for processing the `org_name` option or argument

    `required` is a boolean for whether org_name is required
    """
    # could be generalized to work for any mutex pair (or list) but no obvious need
    def callback(ctx, param, value):
        """Callback which enforces mutex and 'required' behaviour (if required)."""
        prev_value = ctx.params.get("org_name")
        if value and prev_value and prev_value != value:
            raise click.UsageError(
                f"Either ORGNAME or --org ORGNAME should be supplied, not both ({value}, {prev_value})"
            )
        ctx.params["org_name"] = value or prev_value
        if required and not ctx.params.get("org_name"):
            raise click.UsageError("Please specify ORGNAME or --org ORGNAME")

    return callback


def orgname_option_or_argument(*, required):
    """Create decorator that allows org_name to be an option or an argument"""

    def decorator(func):
        if required:
            message = "One of ORGNAME (see above) or --org is required."
        else:
            message = "By default, runs against the current default org."

        opt_version = click.option(
            "--org",
            callback=set_org_name(
                False
            ),  # never required because arg-version may be specified
            expose_value=False,
            help=f"Alternate way to specify the target org. {message}",
        )
        # "required" checking is handled in the callback because it has more context
        # about whether its already seen it.
        arg_version = click.argument(
            "orgname",
            required=False,
            callback=set_org_name(required),
            expose_value=False,
        )
        return arg_version(opt_version(func))

    return decorator


@org.command(
    name="browser",
    help="Opens a browser window and logs into the org using the stored OAuth credentials",
)
@orgname_option_or_argument(required=False)
@click.option(
    "-p",
    "--path",
    required=False,
    help="Navigate to the specified page after logging in.",
)
@click.option(
    "-r",
    "--url-only",
    is_flag=True,
    help="Display the target URL, but don't open a browser.",
)
@pass_runtime(require_project=False, require_keychain=True)
def org_browser(runtime, org_name, path, url_only):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)

    target = org_config.start_url
    if path:
        ret_url = urlencode({"retURL": path})
        target = f"{target}&{ret_url}"

    if url_only:
        click.echo(target)
    else:
        webbrowser.open(target)

    # Save the org config in case it was modified
    org_config.save()


def setup_client(connected_app, login_url=None, sandbox=None) -> OAuth2Client:
    """Provides an OAuth2Client for connecting an Org"""
    if login_url:
        base_uri = login_url
    elif sandbox:
        base_uri = SANDBOX_LOGIN_URL
    elif connected_app.login_url:
        base_uri = connected_app.login_url
    else:
        base_uri = PROD_LOGIN_URL
    base_uri = base_uri.rstrip("/")

    sf_client_config = OAuth2ClientConfig(
        client_id=connected_app.client_id,
        client_secret=connected_app.client_secret,
        redirect_uri=connected_app.callback_url,
        auth_uri=f"{base_uri}/services/oauth2/authorize",
        token_uri=f"{base_uri}/services/oauth2/token",
        scope="web full refresh_token",
    )
    return OAuth2Client(sf_client_config)


def connect_org_to_keychain(
    client: OAuth2Client,
    runtime,
    global_org: bool,
    org_name: str,
    connected_app: str,
) -> None:
    """Use the given client to authorize into an org, and save the
    new OrgConfig to the keychain."""
    oauth_dict = client.auth_code_flow(prompt="login")

    global_org = global_org or runtime.project_config is None
    org_config = OrgConfig(oauth_dict, org_name, runtime.keychain, global_org)
    org_config.config["connected_app"] = connected_app
    org_config.load_userinfo()
    org_config.populate_expiration_date()

    org_config.save()


@org.command(
    name="connect", help="Connects a new org's credentials using OAuth Web Flow"
)
@orgname_option_or_argument(required=True)
@click.option(
    "--connected-app",
    "--connected_app",
    "connected_app_name",
    help="Name of the connected_app service to use.",
)
@click.option(
    "--sandbox", is_flag=True, help="If set, connects to a Salesforce sandbox org"
)
@click.option(
    "--login-url",
    help="If set, login to this hostname.",
)
@click.option(
    "--default",
    is_flag=True,
    help="If set, sets the connected org as the new default org",
)
@click.option(
    "--global-org",
    help="If set, the connected org is available to all CumulusCI projects.",
    is_flag=True,
)
@pass_runtime(require_project=False, require_keychain=True)
def org_connect(
    runtime, org_name, sandbox, login_url, default, global_org, connected_app_name=None
):
    runtime.check_org_overwrite(org_name)

    if login_url and ".lightning." in login_url:
        raise click.UsageError(
            "Connecting an org with a lightning.force.com URL does not work. "
            "Use the my.salesforce.com version instead"
        )

    connected_app_name = (
        connected_app_name or runtime.keychain.get_default_service_name("connected_app")
    )
    click.echo(f"Connecting org using the {connected_app_name} connected app...")
    connected_app = runtime.keychain.get_service("connected_app", connected_app_name)
    sf_client = setup_client(connected_app, login_url, sandbox)
    connect_org_to_keychain(
        sf_client, runtime, global_org, org_name, connected_app_name
    )

    if default and runtime.project_config is not None:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")


@org.command(name="default", help="Sets an org as the default org for tasks and flows")
@orgname_option_or_argument(required=False)
@click.option(
    "--unset",
    is_flag=True,
    help="Unset the org as the default org leaving no default org selected",
)
@pass_runtime(require_keychain=True)
def org_default(runtime, org_name, unset):
    if unset:
        runtime.keychain.unset_default_org()
        click.echo("Default org unset")
    elif org_name:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")
    else:
        orgname, org_config = runtime.keychain.get_default_org()
        if orgname:
            click.echo(f"{orgname} is the default org")
        else:
            click.echo("There is no default org")


@org.command(name="import", help="Import an org from Salesforce DX")
@click.argument("username_or_alias")
@orgname_option_or_argument(required=True)
@pass_runtime(require_keychain=True)
def org_import(runtime: CliRuntime, username_or_alias: str, org_name: str):
    # Import the org from the SFDX keychain as an SfdxOrgConfig
    # The `sfdx` key ensures we can reload using the right class.
    org_config = SfdxOrgConfig(
        {"username": username_or_alias, "sfdx": True},
        org_name,
        runtime.keychain,
        global_org=False,
    )

    # Determine if we received a locally-created scratch org
    # or some other org (which we'll treat as persistent)

    info = org_config.sfdx_info
    if info.get("created_date"):
        # This is a locally-created scratch org.
        # Re-import accordingly.
        org_config = ScratchOrgConfig(
            {"username": username_or_alias},
            org_name,
            runtime.keychain,
            global_org=False,
        )
        org_config._sfdx_info = info
        # Set `created` so we don't try to rebuild it.
        org_config.config["created"] = True

        org_config.config["days"] = calculate_org_days(info)
        org_config.config["date_created"] = parse_api_datetime(info["created_date"])

        org_config.save()
        click.echo(
            "Imported scratch org: {org_id}, username: {username}".format(
                **org_config.sfdx_info
            )
        )
    else:
        # This is either a persistent org or a scratch org imported into the
        # sfdx keychain via OAuth login.
        org_config.populate_expiration_date()
        org_config.save()
        click.echo(
            "Imported org: {org_id}, username: {username}".format(
                **org_config.sfdx_info
            )
        )


def calculate_org_days(info):
    """Returns the difference in days between created_date (ISO 8601),
    and expiration_date (%Y-%m-%d)"""
    if not info.get("created_date") or not info.get("expiration_date"):
        return 1
    created_date = parse_api_datetime(info["created_date"]).date()
    expires_date = datetime.strptime(info["expiration_date"], "%Y-%m-%d").date()
    return abs((expires_date - created_date).days)


@org.command(name="info", help="Display information for a connected org")
@orgname_option_or_argument(required=False)
@click.option(
    "print_json", "--json", is_flag=True, help="Print as JSON.  Includes access token."
)
@pass_runtime(require_project=False, require_keychain=True)
def org_info(runtime, org_name, print_json):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain, print_json)
    console = Console()
    if print_json:
        click.echo(
            json.dumps(
                org_config.config,
                sort_keys=True,
                indent=4,
                default=str,
                separators=(",", ": "),
            )
        )
    else:
        ui_key_set = {
            "config_file",
            "config_name",
            "connected_app",
            "created",
            "date_created",
            "days",
            "default",
            "email_address",
            "instance_url",
            "instance_name",
            "is_sandbox",
            "namespace",
            "namespaced",
            "org_id",
            "org_type",
            "password",
            "scratch",
            "scratch_org_type",
            "set_password",
            "serialization_format",  # only during the transition
            "sfdx_alias",
            "username",
        }
        keys = ui_key_set.intersection(org_config.config.keys())
        pairs = [[key, str(org_config.config[key])] for key in keys]
        pairs.append(["api_version", org_config.latest_api_version])
        pairs.sort()
        table_data = [[f"Org: {org_name}", ""]]
        table_data.extend(
            [[click.style(key, bold=True), value] for key, value in pairs]
        )
        table = CliTable(
            table_data,
        )
        console.print(table)

        if org_config.scratch and org_config.expires:
            console.print("Org expires on {:%c}".format(org_config.expires))

    # Save the org config in case it was modified
    org_config.save()


@org.command(name="list", help="Lists all orgs in scope for the current project")
@click.option("--plain", is_flag=True, help="Print the table using plain ascii.")
@click.option(
    "--json", "json_flag", is_flag=True, help="Output results in JSON format."
)
@pass_runtime(require_project=False, require_keychain=True)
def org_list(runtime, json_flag, plain):
    def _get_org_safe(org):
        try:
            return runtime.keychain.get_org(org)
        except Exception as e:
            click.echo(f"Cannot load org config for `{org}`: {e}")

    plain = plain or runtime.universal_config.cli__plain_output
    org_configs = ((org, _get_org_safe(org)) for org in runtime.keychain.list_orgs())
    org_configs = {org: org_config for org, org_config in org_configs if org_config}

    json_data = {}
    try:
        default_org_name, _ = runtime.keychain.get_default_org()
    except Exception:  # pragma: no cover
        default_org_name = None

    for org, org_config in org_configs.items():
        is_org_default = org == default_org_name
        row_data = {"is_default": is_org_default, "name": org}
        row_data.update(_get_org_dict(org_config))
        json_data[row_data["name"]] = row_data

    if json_flag:
        click.echo(json.dumps(json_data))
        return

    console = Console()
    scratch_table, persistent_table = _make_tables(json_data)
    console.print(scratch_table, justify="left")
    console.print(persistent_table, justify="left")

    try:
        runtime.keychain.cleanup_org_cache_dirs()
    except Exception:
        click.echo(
            "Cannot cleanup org cache dirs, perhaps due to org config files which cannot be decrypted."
        )


def _make_tables(json_data: dict):
    scratch_keys = [
        key for key, row_dict in json_data.items() if row_dict.pop("is_scratch")
    ]
    scratch_data = [["Default", "Name", "Days", "Expired", "Config", "Domain"]]
    scratch_data.extend([list(json_data.pop(k).values()) for k in scratch_keys])

    rows_to_dim = [row_index for row_index, row in enumerate(scratch_data) if row[3]]
    scratch = CliTable(scratch_data, title="Scratch Orgs", dim_rows=rows_to_dim)

    persistent_data = [["Default", "Name", "Username", "Expires"]]
    persistent_data.extend([list(row_dict.values()) for row_dict in json_data.values()])
    persistent = CliTable(persistent_data, title="Connected Orgs")

    return scratch.table, persistent.table


def _get_org_dict(org_config):
    if isinstance(org_config, ScratchOrgConfig):
        return _format_scratch_org_data(org_config)
    else:
        return {
            "username": org_config.config.get(
                "username", org_config.userinfo__preferred_username
            ),
            "expires": org_config.expires or "Unknown",
            "is_scratch": False,
        }


def _format_scratch_org_data(org_config):
    org_days = org_config.format_org_days()
    if org_config.expired:
        domain = ""
    else:
        instance_url = org_config.config.get("instance_url", "")
        domain = (urlparse(instance_url).hostname or "").replace(
            ".my.salesforce.com", ""
        )
    return {
        "days": org_days,
        "expired": org_config.expired,
        "config": org_config.config_name,
        "domain": domain,
        "is_scratch": True,
    }


@org.command(
    name="prune", help="Removes all expired scratch orgs from the current project"
)
@click.option(
    "--include-active",
    is_flag=True,
    help="Remove all scratch orgs, regardless of expiry.",
)
@pass_runtime(require_project=True, require_keychain=True)
def org_prune(runtime, include_active=False):

    predefined_scratch_configs = runtime.project_config.lookup("orgs__scratch", {})

    expired_orgs_removed = []
    active_orgs_removed = []
    org_shapes_skipped = []
    active_orgs_skipped = []
    for org_name in runtime.keychain.list_orgs():

        org_config = runtime.keychain.get_org(org_name)

        if org_name in predefined_scratch_configs:
            if org_config.active and include_active:
                runtime.keychain.remove_org(org_name)
                active_orgs_removed.append(org_name)
            else:
                org_shapes_skipped.append(org_name)

        elif org_config.active:
            if include_active:
                runtime.keychain.remove_org(org_name)
                active_orgs_removed.append(org_name)
            else:
                active_orgs_skipped.append(org_name)

        elif isinstance(org_config, ScratchOrgConfig):
            runtime.keychain.remove_org(org_name)
            expired_orgs_removed.append(org_name)

    if expired_orgs_removed:
        click.echo(
            f"Successfully removed {len(expired_orgs_removed)} expired scratch orgs: {', '.join(expired_orgs_removed)}"
        )
    else:
        click.echo("No expired scratch orgs to delete. ✨")

    if active_orgs_removed:
        click.echo(
            f"Successfully removed {len(active_orgs_removed)} active scratch orgs: {', '.join(active_orgs_removed)}"
        )
    elif include_active:
        click.echo("No active scratch orgs to delete. ✨")

    if org_shapes_skipped:
        click.echo(f"Skipped org shapes: {', '.join(org_shapes_skipped)}")

    if active_orgs_skipped:
        click.echo(f"Skipped active orgs: {', '.join(active_orgs_skipped)}")


@org.command(name="remove", help="Removes an org from the keychain")
@orgname_option_or_argument(required=True)
@click.option(
    "--global-org",
    is_flag=True,
    help="Set this option to force remove a global org.  Default behavior is to error if you attempt to delete a global org.",
)
@pass_runtime(require_project=False, require_keychain=True)
def org_remove(runtime, org_name, global_org):
    try:
        org_config = runtime.keychain.get_org(org_name)
    except OrgNotFound:
        raise click.ClickException(f"Org {org_name} does not exist in the keychain")

    if org_config.can_delete():
        click.echo("A scratch org was already created, attempting to delete...")
        try:
            org_config.delete_org()
        except Exception as e:
            click.echo(e)
            click.echo("Perhaps it was already deleted?")
            click.echo("Removing org regardless.")

    global_org = global_org or runtime.project_config is None
    runtime.keychain.remove_org(org_name, global_org)


@org.command(
    name="scratch", help="Connects a Salesforce DX Scratch Org to the keychain"
)
@click.argument("config_name")
@orgname_option_or_argument(required=True)
@click.option(
    "--default",
    is_flag=True,
    help="If set, sets the connected org as the new default org",
)
@click.option(
    "--devhub", help="If provided, overrides the devhub used to create the scratch org"
)
@click.option(
    "--days",
    help="If provided, overrides the scratch config default days value for how many days the scratch org should persist",
)
@click.option(
    "--no-password", is_flag=True, help="If set, don't set a password for the org"
)
@click.option(
    "--release",
    help="If provided, specify either previous or preview when creating a scratch org",
)
@pass_runtime(require_keychain=True)
def org_scratch(
    runtime, config_name, org_name, default, devhub, days, no_password, release=None
):
    runtime.check_org_overwrite(org_name)
    release_options = ["previous", "preview"]
    if release and release not in release_options:
        raise click.UsageError(
            "Release options value is not valid. Either specify preview or previous."
        )

    scratch_configs = runtime.project_config.lookup("orgs__scratch")
    if not scratch_configs:
        raise click.UsageError("No scratch org configs found in cumulusci.yml")
    scratch_config = scratch_configs.get(config_name)
    if not scratch_config:
        raise click.UsageError(
            f"No scratch org config named {config_name} found in the cumulusci.yml file"
        )

    if devhub:
        scratch_config["devhub"] = devhub

    runtime.keychain.create_scratch_org(
        org_name, config_name, days, set_password=not (no_password), release=release
    )

    if default:
        runtime.keychain.set_default_org(org_name)
        click.echo(f"{org_name} is now the default org")
    else:
        click.echo(f"{org_name} is configured for use")


@org.command(
    name="scratch_delete",
    help="Deletes a Salesforce DX Scratch Org leaving the config in the keychain for regeneration",
)
@orgname_option_or_argument(required=True)
@pass_runtime(require_keychain=True)
def org_scratch_delete(runtime, org_name):
    org_config = runtime.keychain.get_org(org_name)
    if not org_config.scratch:
        raise click.UsageError(f"Org {org_name} is not a scratch org")

    try:
        org_config.delete_org()
    except Exception as e:
        click.echo(e)
        click.echo(f"Use `cci org remove {org_name}` to remove it from your keychain.")
        return

    org_config.save()


org_shell_cci_help_message = """
The cumulusci shell gives you access to the following objects and functions:

* sf - simple_salesforce connected to your org. [1]
* org_config - local information about your org. [2]
* project_config - information about your project. [3]
* tooling - simple_salesforce connected to the tooling API on your org.
* query() - SOQL query. `help(query)` for more information
* describe() - Inspect object fields. `help(describe)` for more information
* help() - for interactive help on Python
* help(obj) - for help on any specific Python object or module

[1] https://github.com/simple-salesforce/simple-salesforce
[2] https://cumulusci.readthedocs.io/en/latest/api/cumulusci.core.config.html#module-cumulusci.core.config.OrgConfig
[3] https://cumulusci.readthedocs.io/en/latest/api/cumulusci.core.config.html#module-cumulusci.core.config.project_config
"""


class CCIHelp(type(help)):
    def __repr__(self):
        return org_shell_cci_help_message


@org.command(
    name="shell",
    help="Drop into a Python shell with a simple_salesforce connection in `sf`, "
    "as well as the `org_config` and `project_config`.",
)
@orgname_option_or_argument(required=False)
@click.option("--script", help="Path to a script to run", type=click.Path())
@click.option("--python", help="Python code to run directly")
@pass_runtime(require_keychain=True)
def org_shell(runtime, org_name, script=None, python=None):
    org_name, org_config = runtime.get_org(org_name)
    org_config.refresh_oauth_token(runtime.keychain)

    sf = get_simple_salesforce_connection(runtime.project_config, org_config)
    tooling = get_simple_salesforce_connection(
        runtime.project_config, org_config, base_url="tooling"
    )

    sf_helpers = SimpleSalesforceUIHelpers(sf)

    globals = {
        "sf": sf,
        "tooling": tooling,
        "org_config": org_config,
        "project_config": runtime.project_config,
        "help": CCIHelp(),
        "query": sf_helpers.query,
        "describe": sf_helpers.describe,
    }

    if script:
        if python:
            raise click.UsageError("Cannot specify both --script and --python")
        runpy.run_path(script, init_globals=globals)
    elif python:
        exec(python, globals)
    else:
        code.interact(
            banner=f"Use `sf` to access org `{org_name}` via simple_salesforce\n"
            + "Type `help` for more information about the cci shell.",
            local=globals,
        )

    # Save the org config in case it was modified
    org_config.save()
