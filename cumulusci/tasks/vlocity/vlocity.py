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
        self, namespace: str, legacy: bool = False, org: str = None
    ) -> str:
        if legacy:
            if org:
                url: str = self.org_config.instance_url.replace(
                    ".{org}.my.salesforce.com",
                    f"--{namespace}.{org}.vf.force.com",
                )
            else:
                url: str = self.org_config.instance_url.replace(
                    ".my.salesforce.com",
                    f"--{namespace}.vf.force.com",
                )
        else:
            if org:
                url: str = self.org_config.instance_url.replace(
                    ".{org}.my.salesforce.com",
                    f"--{namespace}.{org}.{self.org_config.instance_name}.visual.force.com",
                )
            else:
                url: str = self.org_config.instance_url.replace(
                    ".my.salesforce.com",
                    f"--{namespace}.{self.org_config.instance_name}.visual.force.com",
                )
        return url

    def prepare_remote_site_urls(self, namespace: str) -> str:
        """ " for paying customers
        or any org type not covered# in documentation
        Enterprise Edition for example not tested.
        """

        dns_zone = ".my.salesforce.com"

        # developer
        if "develop.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "develop")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "develop")

            # str = self.org_config.instance_url.replace(
            #     ".develop.my.salesforce.com",
            #     f"--{namespace}.develop.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".develop.my.salesforce.com",
            #     f"--{namespace}.develop.vf.force.com",
            # )
        # patch
        elif "patch.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "patch")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "patch")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".patch.my.salesforce.com",
            #     f"--{namespace}.patch.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".patch.my.salesforce.com",
            #     f"--{namespace}.patch.vf.force.com",
            # )
        # trailhead
        elif "trailblaze.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "trailblaze")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "trailblaze")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".trailblaze.my.salesforce.com",
            #     f"--{namespace}.trailblaze.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".trailblaze.my.salesforce.com",
            #     f"--{namespace}.trailblaze.vf.force.com",
            # )
        # scratch
        elif "scratch.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "scratch")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "scratch")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".scratch.my.salesforce.com",
            #     f"--{namespace}.scratch.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".scratch.my.salesforce.com",
            #     f"--{namespace}.scratch.vf.force.com",
            # )
        # sandbox
        elif "sandbox.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "sandbox")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "sandbox")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".sandbox.my.salesforce.com",
            #     f"--{namespace}.sandbox.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".sandbox.my.salesforce.com",
            #     f"--{namespace}.sandbox.vf.force.com",
            # )
        # demo
        elif "demo.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "demo")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "demo")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".demo.my.salesforce.com",
            #     f"--{namespace}.demo.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".demo.my.salesforce.com",
            #     f"--{namespace}.demo.vf.force.com",
            # )
        # free
        elif "free.my.salesforce.com" in self.org_config.instance_url:
            visualforce_url = self.create_vf_url(namespace, False, "free")
            legacy_visualforce_url = self.create_vf_url(namespace, True, "free")
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".free.my.salesforce.com",
            #     f"--{namespace}.free.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".free.my.salesforce.com",
            #     f"--{namespace}.free.vf.force.com",
            # )
        else:
            visualforce_url = self.create_vf_url(namespace, False, None)
            legacy_visualforce_url = self.create_vf_url(namespace, True, None)
            # visualforce_url: str = self.org_config.instance_url.replace(
            #     ".my.salesforce.com",
            #     f"--{namespace}.{self.org_config.instance_name}.visual.force.com",
            # )
            # legacy_visualforce_url: str = self.org_config.instance_url.replace(
            #     ".my.salesforce.com",
            #     f"--{namespace}.vf.force.com",
            # )
        lightning_url: str = self.org_config.instance_url.replace(
            ".my.salesforce.com", ".lightning.force.com"
        )
        # if self.org_config.org_type in ["Patch", "Scratch", "Sandbox", "Free"]:
        #     dns_zone = f"{self.org_config.org_type}{dns_zone}"
        #     org_type = self.org_config.org_type.lower()
        # elif self.org_config.org_type == "Developer Edition":
        #     dns_zone = f".develop{dns_zone}"
        #     org_type = "develop"
        # elif self.org_config.org_type == "Trailhead Playground":
        #     dns_zone = f".trailblaze{dns_zone}"
        #     org_type = "trailblaze"
        # elif self.org_config.org_type == "Patch":
        #     dns_zone = f".patch{dns_zone}"
        #     org_type = "patch"
        # elif self.org_config.org_type == "Demonstration":
        #     dns_zone = f".demo{dns_zone}"
        #     org_type = "demo"
        # breakpoint()
        # visualforce_url: str = self.org_config.instance_url.replace(
        #     dns_zone,
        #     f"--{namespace}.{org_type}.{self.org_config.instance_name}.visual.force.com",
        # )
        # legacy_visualforce_url: str = self.org_config.instance_url.replace(
        #     dns_zone,
        #     f"--{namespace}.{org_type}.vf.force.com",
        # )
        # lightning_url: str = self.org_config.instance_url.replace(
        #     dns_zone, ".lightning.force.com"
        # )
        breakpoint()
        return {
            "visualforce_url": visualforce_url,
            "legacy_visualforce_url": legacy_visualforce_url,
            "lightning_url": lightning_url,
        }

    def _get_options(self) -> RSSOptions:
        namespace = self.options.get("namespace") or OMNI_NAMESPACE
        urls = self.prepare_remote_site_urls(namespace)
        breakpoint()
        if ".scratch.my" in self.org_config.instance_url:
            visualforce_url: str = self.org_config.instance_url.replace(
                ".scratch.my.salesforce.com",
                f"--{namespace}.scratch.{self.org_config.instance_name}.visual.force.com",
            )
            legacy_visualforce_url: str = self.org_config.instance_url.replace(
                ".scratch.my.salesforce.com",
                f"--{namespace}.scratch.vf.force.com",
            )
        else:
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
        breakpoint()
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
