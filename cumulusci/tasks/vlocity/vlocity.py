import os
import re
import sys
from abc import ABC
from pathlib import Path
from typing import Final

import sarge

from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.core.exceptions import SfdxOrgException
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.tasks.command import Command
from cumulusci.tasks.metadata_etl.remote_site_settings import (
    AddRemoteSiteSettings,
    RSSOptions,
)
from cumulusci.tasks.vlocity.exceptions import BuildToolMissingError

CLI_KEYWORD = "vlocity"
BUILD_TOOL_MISSING_ERROR = (
    "This task requires the Vlocity Build CLI tool which is not currently installed on this system. "
    "For information on installing this tool visit: https://github.com/vlocityinc/vlocity_build#vlocity-build"
)
VF_RSS_NAME = "OmniStudioVisualforce"
VF_LEGACY_RSS_NAME = "OmniStudioLegacyVisualforce"
LWC_RSS_NAME = "OmniStudioLightning"
OMNI_NAMESPACE = "omnistudio"
VBT_SF_ALIAS = "cci-vbt-target"
SF_TOKEN_ENV = "SF_ACCESS_TOKEN"
VBT_TOKEN_ENV = "OMNIOUT_TOKEN"


class VlocityBaseTask(Command, BaseSalesforceTask):
    """Call the vlocity build tool cli with params"""

    task_options: dict = {
        "command": {
            "description": "The full command to run with the sfdx cli.",
            "required": True,
        },
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
    }

    def _init_options(self, kwargs):
        kwargs.setdefault("interactive", sys.stdout.isatty())
        return super()._init_options(kwargs)

    def _init_task(self):
        tool_exists = self._vlocity_build_tool_exists()
        if not tool_exists:
            raise BuildToolMissingError(BUILD_TOOL_MISSING_ERROR)

    def _vlocity_build_tool_exists(self) -> bool:
        try:
            p = sarge.Command("vlocity", stdout=sarge.Capture(buffer_size=-1))
            p.run(async_=True)
            p.wait()
        except ValueError:
            return False
        else:
            return True

    def _get_command(self) -> str:
        command: str = f"{CLI_KEYWORD} {self.options['command']}"

        if extra_options := self.options.get("extra"):
            command += f" {extra_options}"
        return command


class VlocitySimpleJobTask(VlocityBaseTask, ABC):
    """Abstract class for working with the `vlocity` CLI tool"""

    task_options: dict = {
        "job_file": {
            "description": "Filepath to the jobfile",
            "required": True,
        },
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
    }

    def _get_command(self) -> str:
        username: str = self.org_config.username
        job_file: str = self.options.get("job_file")

        command: str = f"{self.command_keyword} -job {job_file}"

        if not isinstance(self.org_config, ScratchOrgConfig):
            username = self._add_token_to_sfdx(
                self.org_config.access_token, self.org_config.instance_url
            )
        command = f"{command} -sfdx.username '{username}'"

        self.options["command"] = command
        return super()._get_command()

    def _add_token_to_sfdx(self, access_token: str, instance_url: str) -> str:
        """
        HACK: VBT's documentation suggests that passing sf.accessToken/sf.instanceUrl
        is compatible with local compilation, but our experience (as of VBT v1.17)
        says otherwise. This function is our workaround: by adding the access token
        and temporarily setting it as the default we allow VBT to deploy the
        locally compiled components via SFDX or salesforce-alm.
        """
        # TODO: Use the sf v2 form of this command instead (when we migrate)
        token_store_cmd = [
            "sf",
            "org",
            "login",
            "access-token",
            "--no-prompt",
            "--alias",
            f"{VBT_SF_ALIAS}",
            "--instance-url",
            f"{instance_url}",
        ]
        try:
            p = sarge.Command(token_store_cmd, env={SF_TOKEN_ENV: access_token})
            p.run(async_=True)
            p.wait()
        except Exception as exc:
            raise SfdxOrgException("token store failed") from exc
        return VBT_SF_ALIAS


class VlocityRetrieveTask(VlocitySimpleJobTask):
    """Runs a `vlocity packExport` command with a given user and job file"""

    command_keyword: Final[str] = "packExport"


class VlocityDeployTask(VlocitySimpleJobTask):
    """Runs a `vlocity packDeploy` command with a given user and job file"""

    command_keyword: Final[str] = "packDeploy"

    task_options: dict = {
        "job_file": {
            "description": "Filepath to the jobfile",
            "required": True,
        },
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
        "npm_auth_key_env": {
            "description": (
                "Environment variable storing an auth token for the "
                "Vlocity NPM Repository (npmAuthKey). If defined, appended "
                "to the job file."
            ),
            "default": VBT_TOKEN_ENV,
        },
    }

    def _get_command(self) -> str:
        npm_env_var: str = self.options.get("npm_auth_key_env", VBT_TOKEN_ENV)
        job_file: str = self.options.get("job_file")

        self.add_npm_auth_to_jobfile(job_file, npm_env_var)

        return super()._get_command()

    def add_npm_auth_to_jobfile(self, job_file: str, npm_env_var: str) -> bool:
        """
        HACK: VBT local compilation requires use of an auth token for a private
        NPM repository, defined as the npmAuthKey option. Unfortunately, this
        option can't be defined in an environment variable, nor can it be passed
        via the CLI. Instead, the option is _only_ read from the job file, so the
        secret must be committed to source control for CI/CD. Our workaround is to
        check for the presence of npm_env_var in the environment, and appending it
        to the job file if it is.

        Retuns:
        - False: No environment variable found or conflict exists in job file
        - True: Auth token written to job file
        """
        found_msg = f"VBT NPM environment variable named '{npm_env_var}' found."
        if npm_key := os.environ.get(npm_env_var):
            self.logger.info(found_msg)
        else:
            self.logger.debug(f"No {found_msg}")
            return False

        job_file_path: Path = Path(job_file)
        job_file_txt = job_file_path.read_text()

        # Warn about duplicate keys to avoid showing the user a nasty JS traceback
        if "npmAuthKey" in job_file_txt:
            self.logger.warning("npmAuthKey present in job file, skipping...")
            return False

        self.logger.info(f"Appending to {job_file}")
        job_file_path.write_text(f"{job_file_txt}\nnpmAuthKey: {npm_key}")
        return True


class OmniStudioDeployRemoteSiteSettings(AddRemoteSiteSettings):
    """Deploys remote site settings needed for OmniStudio.
    This cannot be configured in cumulusci/cumulusci.yml because
    the values for the 'url' field are dynamic."""

    task_options: dict = {
        "namespace": {
            "description": f"The namespace to inject into RemoteSiteSettings.url values. Defaults to '{OMNI_NAMESPACE}'."
        }
    }

    def _get_options(self) -> RSSOptions:
        namespace = self.options.get("namespace") or OMNI_NAMESPACE
        urls = prepare_remote_site_urls(
            self.org_config.instance_url,
            self.org_config.instance_name,
            namespace,
        )
        self.options = {
            **self.options,
            "records": [
                {
                    "full_name": VF_RSS_NAME,
                    "url": urls["visualforce_url"],
                    "is_active": True,
                },
                {
                    "full_name": VF_LEGACY_RSS_NAME,
                    "url": urls["legacy_visualforce_url"],
                    "is_active": True,
                },
                {
                    "full_name": LWC_RSS_NAME,
                    "url": urls["lightning_url"],
                    "is_active": True,
                },
            ],
        }
        return super()._get_options()


def create_vf_url(
    namespace: str,
    instance_url: str,
    legacy: bool = False,
    instance: str = None,
    org: str = None,
    dns: str = ".my.salesforce.com",
):
    """
    Helper function to create visualforce or legacy visualforce
    remote site settings. Function takes a namespace,and injects it
    into remote site setting url provided.

    A legacy boolean parameter is passed to determine whether to construct
    the legacy or visualforce url convention.

    An optional org parameter is available to determine the url convention
    to inject the org type into the remote site setting url
    to follow the appropriate convention.

    Lastly an optional dns value is given to abstract away the common
    .my.salesforce.com convention that is common for all instance urls.
    """
    if legacy:
        if org:
            url = instance_url.replace(
                f".{org}{dns}", f"--{namespace}.{org}.vf.force.com"
            )
        else:
            url = instance_url.replace(f"{dns}", f"--{namespace}.vf.force.com")
    else:
        if org:
            url = instance_url.replace(
                f".{org}{dns}",
                f"--{namespace}.{instance}.visual.force.com",
            )
        else:
            url = instance_url.replace(
                f"{dns}",
                f"--{namespace}.{instance}.visual.force.com",
            )
    return url


def prepare_remote_site_urls(
    instance_url: str,
    instance: str,
    namespace: str,
    dns: str = ".my.salesforce.com",
):
    """
    Helper function to create all 3 remote site settings required
    for Omnistudio Development.

    This includes the following remote site settings:

    - visualforce remote site setting (helper function used)
    - legacy_visualforce remote site setting (helper function used)
    - lightning (web component) remote site setting

    Lastly an optional dns value is given to abstract away the common
    .my.salesforce.com convention that is common for all instance urls.
    """

    match = re.match(f"(?P<Name>[^.]+)\\.(?P<Category>[^.]+){dns}", instance_url)
    category = None
    if match:
        category = match.group("Category")

    if category and f"{category}{dns}" in instance_url:
        visualforce_url = create_vf_url(
            namespace,
            instance_url,
            False,
            instance,
            category,
        )
        legacy_visualforce_url = create_vf_url(
            namespace,
            instance_url,
            True,
            instance,
            category,
        )
    else:
        visualforce_url = create_vf_url(
            namespace,
            instance_url,
            False,
            instance,
            None,
        )
        legacy_visualforce_url = create_vf_url(
            namespace,
            instance_url,
            True,
            instance,
            None,
        )

    lightning_url = instance_url.replace(f"{dns}", ".lightning.force.com")
    return {
        "visualforce_url": visualforce_url,
        "legacy_visualforce_url": legacy_visualforce_url,
        "lightning_url": lightning_url,
    }
