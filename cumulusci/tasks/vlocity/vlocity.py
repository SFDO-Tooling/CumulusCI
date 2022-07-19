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


class VlocityBaseTask(Command, BaseSalesforceTask):
    """Call the vlocity build tool cli with params"""

    task_options: dict = {
        "command": {
            "description": "The full command to run with the sfdx cli.",
            "required": True,
        },
        "extra": {"description": "Any extra arguments to pass to the vlocity CLI"},
    }

    def _init_task(self):
        tool_exists = self._vlocity_build_tool_exists()
        if not tool_exists:
            raise BuildToolMissingError(BUILD_TOOL_MISSING_ERROR)

    def _vlocity_build_tool_exists(self) -> bool:
        command = "vlocity --json"
        p = sarge.Command(command, stdout=sarge.Capture(buffer_size=-1))
        p.run(async_=True)
        p.wait()
        return p.returncode == 0

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
        username = self.org_config.username
        job_file = self.options.get("job_file")

        command: str = f"{self.command_keyword} -job {job_file}"

        if isinstance(self.org_config, ScratchOrgConfig):
            command = f"{command} -sfdx.username '{username}'"
        else:
            command = f"{command} -sf.accesstoken '{self.org_config.access_token}' -sf.instanceUrl '{self.org_config.instance_url}'"

        self.options["command"] = command
        return super()._get_command()


class VlocityRetrieveTask(VlocitySimpleJobTask):
    """Runs a `vlocity packExport` command with a given user and job file"""

    command_keyword: Final[str] = "packExport"


class VlocityDeployTask(VlocitySimpleJobTask):
    """Runs a `vlocity packDeploy` command with a given user and job file"""

    command_keyword: Final[str] = "packDeploy"
