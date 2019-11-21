import os
import sys
from subprocess import call

import click
import keyring
import pkg_resources

from cumulusci import __version__
from cumulusci.core.runtime import BaseCumulusCI
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.utils import import_global
from cumulusci.utils import get_cci_upgrade_command
from cumulusci.utils import random_alphanumeric_underscore

# Environment Variables
KEYCHAIN_CLASS_ENV = "CUMULUSCI_KEYCHAIN_CLASS"
CUMULUSCI_KEY_ENV = "CUMULUSCI_KEY"


class CliRuntime(BaseCumulusCI):
    def __init__(self, *args, **kwargs):
        try:
            super(CliRuntime, self).__init__(*args, **kwargs)
        except (ProjectConfigNotFound, NotInProject) as e:
            raise click.UsageError(str(e))
        except ConfigError as e:
            raise click.UsageError(f"Config Error: {str(e)}")
        except (KeychainKeyNotFound) as e:
            raise click.UsageError(f"Keychain Error: {str(e)}")

    def get_keychain_class(self):
        default_keychain_class = (
            self.project_config.cumulusci__keychain
            if not self.is_global_keychain
            else self.global_config.cumulusci__keychain
        )
        keychain_class = os.environ.get(KEYCHAIN_CLASS_ENV, default_keychain_class)
        return import_global(keychain_class)

    def get_keychain_key(self):
        key_from_env = os.environ.get(CUMULUSCI_KEY_ENV)
        try:
            key_from_keyring = keyring.get_password("cumulusci", CUMULUSCI_KEY_ENV)
            has_functioning_keychain = True
        except Exception:
            key_from_keyring = None
            has_functioning_keychain = False
        # If no key in environment or file, generate one
        key = key_from_env or key_from_keyring
        if key is None:
            if has_functioning_keychain:
                key = random_alphanumeric_underscore(length=16)
            else:
                raise KeychainKeyNotFound(
                    "Unable to store CumulusCI encryption key. "
                    f"You can configure it manually by setting the {CUMULUSCI_KEY_ENV} "
                    "environment variable to a random 16-character string."
                )
        if has_functioning_keychain and not key_from_keyring:
            keyring.set_password("cumulusci", CUMULUSCI_KEY_ENV, key)
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

    def get_org(self, org_name=None, fail_if_missing=True, no_prompt=False):
        if org_name:
            org_config = self.keychain.get_org(org_name)
        else:
            org_name, org_config = self.keychain.get_default_org()
        if org_config:
            org_config = self.check_org_expired(
                org_name, org_config, no_prompt=no_prompt
            )
        elif fail_if_missing:
            raise click.UsageError("No org specified and no default org set.")
        return org_name, org_config

    def check_org_expired(self, org_name, org_config, no_prompt):
        if org_config.scratch and org_config.date_created and org_config.expired:
            click.echo(click.style("The scratch org is expired", fg="yellow"))
            if self._should_recreate_expired_org(no_prompt):
                self.keychain.create_scratch_org(
                    org_name,
                    org_config.config_name,
                    days=org_config.days,
                    set_password=org_config.set_password,
                )
                click.echo(
                    "Org config was refreshed, attempting to recreate scratch org"
                )
                org_config = self.keychain.get_org(org_name)
                org_config.create_org()
            else:
                raise click.ClickException(
                    f"The target scratch org is expired.  You can use cci org remove {org_name} "
                    "to remove the org and then recreate the config manually"
                )

        return org_config

    def _should_recreate_expired_org(self, no_prompt):
        if not no_prompt:
            return click.confirm("Attempt to recreate the scratch org?", default=True)
        else:
            return no_prompt

    def check_org_overwrite(self, org_name):
        try:
            org = self.keychain.get_org(org_name)
            if org.scratch:
                if org.created:
                    raise click.ClickException(
                        f"Scratch org has already been created. Use `cci org scratch_delete {org_name}"
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


CliConfig = CliRuntime


def get_installed_version():
    """ returns the version name (e.g. 2.0.0b58) that is installed """
    return pkg_resources.parse_version(__version__)
