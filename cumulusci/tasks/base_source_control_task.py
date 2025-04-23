from cumulusci.core.source_action import get_provider
from cumulusci.core.tasks import BaseTask


class BaseSourceControlTask(BaseTask):
    def _init_task(self):
        super()._init_task()
        klass = get_provider(self.project_config)
        service_config = self.project_config.keychain.get_service(klass.service_type)
        self.provider = klass(None, service_config.name, self.project_config.keychain)

    def get_repo(self):
        return self.provider.get_repository()
