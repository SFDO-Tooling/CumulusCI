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

    def _get_options(self) -> RSSOptions:
        namespace = self.options.get("namespace") or OMNI_NAMESPACE

        visualforce_url: str = self.org_config.instance_url.replace(
            ".my.salesforce.com",
            f"--{namespace}.{self.org_config.instance_name}.visual.force.com",
        )
        legacy_visualforce_url: str = self.org_config.instance_url.replace(
            ".my.salesforce.com",
            f"--{namespace}.vf.force.com",
        )
        lightning_url: str = self.org_config.instance_url.replace(
            ".my.salesforce.com", ".lightning.force.com"
        )

        self.options = {
            **self.options,
            "records": [
                {
                    "full_name": VF_RSS_NAME,
                    "url": visualforce_url,
                    "is_active": True,
                },
                {
                    "full_name": VF_LEGACY_RSS_NAME,
                    "url": legacy_visualforce_url,
                    "is_active": True,
                },
                {
                    "full_name": LWC_RSS_NAME,
                    "url": lightning_url,
                    "is_active": True,
                },
            ],
        }
        return super()._get_options()
