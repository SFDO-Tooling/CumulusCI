from cumulusci.core.config import ServiceConfig
from cumulusci.core.tasks import BaseTask
from cumulusci.vcs.base import VCSService
from cumulusci.vcs.bootstrap import get_service
from cumulusci.vcs.models import AbstractRepo


class BaseSourceControlTask(BaseTask):
    def _init_task(self):
        """Initialize the task by setting up the VCS service provider."""
        super()._init_task()
        klass: VCSService = get_service(self.project_config)
        service_config: ServiceConfig = self.project_config.keychain.get_service(
            klass.service_type
        )
        self.vcs_service: VCSService = klass(
            None, service_config.name, self.project_config.keychain
        )

    def get_repo(self) -> AbstractRepo:
        """Returns the repository object for the VCS service."""
        return self.vcs_service.get_repository()
