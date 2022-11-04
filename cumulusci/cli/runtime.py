import functools
import os
import sys
from logging import getLogger
from subprocess import call

import click
import keyring
import pkg_resources

from cumulusci.cli.utils import get_installed_version
from cumulusci.core.exceptions import ConfigError, KeychainKeyNotFound, OrgNotFound
from cumulusci.core.runtime import BaseCumulusCI
from cumulusci.core.utils import import_global
from cumulusci.utils import get_cci_upgrade_command, random_alphanumeric_underscore

logger = getLogger(__name__)


class CliRuntime(BaseCumulusCI):
    def __init__(self, *args, **kwargs):
        try:
            super(CliRuntime, self).__init__(*args, **kwargs)
        except ConfigError as e:
            raise click.UsageError(f"Config Error: {str(e)}")
        except (KeychainKeyNotFound) as e:
            raise click.UsageError(f"Keychain Error: {str(e)}")

    def get_keychain_class(self):
        default_keychain_class = (
            self.project_config.cumulusci__keychain
            if self.project_config is not None
            else self.universal_config.cumulusci__keychain
        )
        keychain_class = os.environ.get(
            "CUMULUSCI_KEYCHAIN_CLASS", default_keychain_class
        )
        if keychain_class:
            return import_global(keychain_class)

    def get_keychain_key(self):
        key_from_env = os.environ.get("CUMULUSCI_KEY")
        keychain_exception = ""
        try:
            key_from_keyring = keyring.get_password("cumulusci", "CUMULUSCI_KEY")
            has_functioning_keychain = True
        except Exception as e:
            keychain_exception = str(e)
            key_from_keyring = None
            has_functioning_keychain = False
        # If no key in environment or file, generate one
        key = key_from_env or key_from_keyring
        if key is None:
            if has_functioning_keychain:
                key = random_alphanumeric_underscore(length=16)
            else:
                # Log why the keychain isn't working,
                # but suppress recommendation to install keyrings.alt on Linux
                keychain_exception = (
                    f"({keychain_exception}) "
                    if "install the keyrings.alt package" not in keychain_exception
                    else ""
                )
                logger.warning(
                    f"Unable to store an encryption key. {keychain_exception}"
                    "Any orgs or services written to disk will not be encrypted. "
                )

        if has_functioning_keychain and not key_from_keyring:
            keyring.set_password("cumulusci", "CUMULUSCI_KEY", key)
        return key

    def alert(self, message="We need your attention!"):
        if self.project_config and self.project_config.dev_config__no_alert:
            return
        click.echo("\a")
        cmd = self._get_platform_alert_cmd(message)
        if cmd:
            try:
                call(cmd)
            except OSError:
                pass  # we don't have the command, probably.

    def _get_platform_alert_cmd(self, message):
        if sys.platform == "darwin":
            notification = message.replace('"', r"\"").replace("'", r"\'")
            return [
                "osascript",
                "-e",
                f'display notification "{notification}" with title "CumulusCI"',
            ]
        elif sys.platform.startswith("linux"):
            return ["notify-send", "--icon=utilities-terminal", "CumulusCI", message]

    def get_org(self, org_name=None, fail_if_missing=True):
        if org_name:
            org_config = self.keychain.get_org(org_name)
        else:
            org_name, org_config = self.keychain.get_default_org()
        if org_config:
            org_config = self.check_org_expired(org_name, org_config)
        elif fail_if_missing:
            raise click.UsageError("No org specified and no default org set.")
        return org_name, org_config

    def check_org_expired(self, org_name, org_config):
        if org_config.scratch and org_config.date_created and org_config.expired:
            click.echo(click.style("The scratch org is expired", fg="yellow"))
            self.keychain.create_scratch_org(
                org_name,
                org_config.config_name,
                days=org_config.days,
                set_password=org_config.set_password,
            )
            click.echo(
                click.style(
                    "Org config was refreshed, attempting to recreate scratch org",
                    fg="yellow",
                )
            )
            org_config = self.keychain.get_org(org_name)
            org_config.create_org()

        return org_config

    def check_org_overwrite(self, org_name):
        try:
            org = self.keychain.get_org(org_name)
            if org.scratch:
                if org.created:
                    raise click.ClickException(
                        f"Scratch org has already been created. Use `cci org scratch_delete {org_name}`"
                    )
            else:
                raise click.ClickException(
                    f"Org {org_name} already exists.  Use `cci org remove` to delete it."
                )
        except OrgNotFound:
            pass
        return True

    def check_cumulusci_version(self):
        if self.project_config:
            min_cci_version = self.project_config.minimum_cumulusci_version
            if min_cci_version:
                parsed_version = pkg_resources.parse_version(min_cci_version)
                if get_installed_version() < parsed_version:
                    raise click.UsageError(
                        f"This project requires CumulusCI version {min_cci_version} or later. "
                        f"To upgrade, please run this command: {get_cci_upgrade_command()}"
                    )

    def get_available_tasks(self):
        return (
            self.project_config.list_tasks()
            if self.project_config is not None
            else self.universal_config.list_tasks()
        )

    def get_available_flows(self):
        return (
            self.project_config.list_flows()
            if self.project_config is not None
            else self.universal_config.list_flows()
        )


# for backwards-compatibility
CliConfig = CliRuntime


def pass_runtime(func=None, require_project=True, require_keychain=False):
    """Decorator which passes the CCI runtime object as the first arg to a click command."""

    def decorate(func):
        @click.pass_context
        def new_func(ctx, *args, **kw):
            runtime = ctx.obj
            if require_project and runtime.project_config is None:
                raise runtime.project_config_error
            if require_keychain:
                runtime._load_keychain()
            func(runtime, *args, **kw)

        return functools.update_wrapper(new_func, func)

    if func is None:
        return decorate
    else:
        return decorate(func)
