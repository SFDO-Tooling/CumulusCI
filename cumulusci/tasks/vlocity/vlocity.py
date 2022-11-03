import sys
from abc import ABC
from typing import Final

import sarge

from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
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
        "job_file": {"description": "Filepath to the jobfile", "required": True},
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
    }

    def _get_command(self) -> str:
        username: str = self.org_config.username
        job_file: str = self.options.get("job_file")

        command: str = f"{self.command_keyword} -job {job_file}"

        if isinstance(self.org_config, ScratchOrgConfig):
            command = f"{command} -sfdx.username '{username}'"
        else:
            access_token: str = f"-sf.accessToken '{self.org_config.access_token}'"
            instance_url: str = f"-sf.instanceUrl '{self.org_config.instance_url}'"
            command = f"{command} {access_token} {instance_url}"

        self.options["command"] = command
        return super()._get_command()


class VlocityRetrieveTask(VlocitySimpleJobTask):
    """Runs a `vlocity packExport` command with a given user and job file"""

    command_keyword: Final[str] = "packExport"


class VlocityDeployTask(VlocitySimpleJobTask):
    """Runs a `vlocity packDeploy` command with a given user and job file"""

    command_keyword: Final[str] = "packDeploy"


class OmniStudioDeployRemoteSiteSettings(AddRemoteSiteSettings):
    """Deploys remote site settings needed for OmniStudio.
    This cannot be configured in cumulusci/cumulusci.yml because
    the values for the 'url' field are dynamic."""

    task_options: dict = {
        "namespace": {
            "description": f"The namespace to inject into RemoteSiteSettings.url values. Defaults to '{OMNI_NAMESPACE}'."
        }
    }

    def create_vf_url(
        self,
        namespace: str,
        legacy: bool = False,
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
                url = self.org_config.instance_url.replace(
                    f".{org}{dns}", f"--{namespace}.{org}.vf.force.com"
                )
                print("EVERYWHERE", url)
            else:
                url = self.org_config.instance_url.replace(
                    f"{dns}", f"--{namespace}.vf.force.com"
                )
        else:
            if org:
                url = self.org_config.instance_url.replace(
                    f".{org}{dns}",
                    f"--{namespace}.{org}.{self.org_config.instance_name}.visual.force.com",
                )
            else:
                url = self.org_config.instance_url.replace(
                    f"{dns}",
                    f"--{namespace}.{self.org_config.instance_name}.visual.force.com",
                )
        return url

    def prepare_remote_site_urls(self, namespace: str, dns: str = ".my.salesforce.com"):
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
        # developer
        if f"develop{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "develop")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "develop")
        # patch
        elif f"patch{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "patch")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "patch")
        # trailhead
        elif f"trailblaze{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "trailblaze")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "trailblaze")
        # scratch
        elif f"scratch{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "scratch")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "scratch")
        # sandbox
        elif f"sandbox{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "sandbox")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "sandbox")
        # demo
        elif f"demo{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "demo")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "demo")
        # free
        elif f"free{dns}" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "free")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "free")
        else:
            visualforce_url = self.create_vf_url(namespace, False, None)
            legacy_visualforce_url = self.create_vf_url(namespace, True, None)

        lightning_url = self.org_config.instance_url.replace(
            f"{dns}", ".lightning.force.com"
        )
        return {
            "visualforce_url": visualforce_url,
            "legacy_visualforce_url": legacy_visualforce_url,
            "lightning_url": lightning_url,
        }

    def _get_options(self) -> RSSOptions:
        namespace = self.options.get("namespace") or OMNI_NAMESPACE
        urls = self.prepare_remote_site_urls(namespace)
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
