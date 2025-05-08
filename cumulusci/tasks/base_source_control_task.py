from cumulusci.core.tasks import BaseTask
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.bootstrap import get_service
from cumulusci.vcs.models import AbstractRepo


class BaseSourceControlTask(BaseTask):
    def _init_task(self):
        """Initialize the task by setting up the VCS service provider."""
        super()._init_task()
        self.vcs_service: VCSService = get_service(
            self.project_config, logger=self.logger
        )

    def get_repo(self) -> AbstractRepo:
        """Returns the repository object for the VCS service."""
        return self.vcs_service.get_repository(options=self.options)
