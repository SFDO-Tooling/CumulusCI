from abc import ABC
from typing import Final

import sarge

from cumulusci.core.config.scratch_org_config import ScratchOrgConfig
from cumulusci.core.tasks import BaseSalesforceTask
from cumulusci.tasks.command import Command
from cumulusci.tasks.vlocity.exceptions import BuildToolMissingError

CLI_KEYWORD = "vlocity"
BUILD_TOOL_MISSING_ERROR = (
    "This task requires the Vlocity Build CLI tool which is not currently installed on this system. "
    "For information on installing this tool visit: https://github.com/vlocityinc/vlocity_build#vlocity-build"
)


class VlocityBaseTask(Command, BaseSalesforceTask, ABC):
    """Call the vlocity build tool cli with params"""

    task_options: dict = {
        "job_file": {"description": "Filepath to the jobfile", "required": True},
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
    }

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
        username: str = self.org_config.username
        job_file: str = self.options.get("job_file")

        command: str = f"{CLI_KEYWORD} {self.command_keyword} -job {job_file} --json"

        if isinstance(self.org_config, ScratchOrgConfig):
            command = f"{command} -sfdx.username '{username}'"
        else:
            access_token: str = f"-sf.accessToken '{self.org_config.access_token}'"
            instance_url: str = f"-sf.instanceUrl '{self.org_config.instance_url}'"
            command = f"{command} {access_token} {instance_url}"

        if extra_options := self.options["extra"]:
            command += f" {extra_options}"

        # The Command parent class expects this option to be set
        self.options["command"] = command
        return super()._get_command()


class VlocityRetrieveTask(VlocityBaseTask):
    """Runs a `vlocity packExport` command with a given user and job file"""

    command_keyword: Final[str] = "packExport"


class VlocityDeployTask(VlocityBaseTask):
    """Runs a `vlocity packDeploy` command with a given user and job file"""

    command_keyword: Final[str] = "packDeploy"
