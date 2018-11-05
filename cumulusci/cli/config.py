import os
import sys
from subprocess import call

import click
import pkg_resources

from cumulusci.core.runtime import BaseCumulusCI
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.exceptions import NotInProject
from cumulusci.core.exceptions import OrgNotFound
from cumulusci.core.exceptions import KeychainKeyNotFound
from cumulusci.core.exceptions import ProjectConfigNotFound
from cumulusci.core.utils import import_class


class CliRuntime(BaseCumulusCI):
    def __init__(self, *args, **kwargs):
        try:
            super(CliRuntime, self).__init__(*args, **kwargs)
        except (ProjectConfigNotFound, NotInProject) as e:
            raise click.UsageError(str(e))
        except ConfigError as e:
            raise click.UsageError("Config Error: {}".format(str(e)))
        except (KeychainKeyNotFound) as e:
            raise click.UsageError("Keychain Error: {}".format(str(e)))

    def get_keychain_class(self):
        keychain_class = os.environ.get(
            "CUMULUSCI_KEYCHAIN_CLASS", self.project_config.cumulusci__keychain
        )
        return import_class(keychain_class)

    def get_keychain_key(self):
        return os.environ.get("CUMULUSCI_KEY")

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
            return [
                "osascript",
                "-e",
                'display notification "{}" with title "{}"'.format(
                    message.replace('"', r"\"").replace("'", r"\'"), "CumulusCI"
                ),
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
            if click.confirm("Attempt to recreate the scratch org?", default=True):
                self.keychain.create_scratch_org(
                    org_name, org_config.config_name, org_config.days
                )
                click.echo(
                    "Org config was refreshed, attempting to recreate scratch org"
                )
                org_config = self.keychain.get_org(org_name)
                org_config.create_org()
            else:
                raise click.ClickException(
                    "The target scratch org is expired.  You can use cci org remove {} "
                    "to remove the org and then recreate the config manually".format(
                        org_name
                    )
                )

        return org_config

    def check_org_overwrite(self, org_name):
        try:
            org = self.keychain.get_org(org_name)
            if org.scratch:
                if org.created:
                    raise click.ClickException(
                        "Scratch org has already been created. "
                        "Use `cci org scratch_delete {}`".format(org_name)
                    )
            else:
                raise click.ClickException(
                    "Org {} already exists.  Use `cci org remove` to delete it.".format(
                        org_name
                    )
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
                        "This project requires CumulusCI version {} or later. "
                        "Please upgrade using pip install -U cumulusci".format(
                            min_cci_version
                        )
                    )


CliConfig = CliRuntime


def get_installed_version():
    """ returns the version name (e.g. 2.0.0b58) that is installed """
    req = pkg_resources.Requirement.parse("cumulusci")
    dist = pkg_resources.WorkingSet().find(req)
    return pkg_resources.parse_version(dist.version)
