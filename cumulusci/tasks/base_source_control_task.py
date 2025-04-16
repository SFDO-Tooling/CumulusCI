from cumulusci.core.source_action import get_provider
from cumulusci.core.tasks import BaseTask


class BaseSourceControlTask(BaseTask):
    def _init_task(self):
        super()._init_task()
        self.provider = get_provider(self.project_config)

    def get_repo(self):
        return self.provider.get_repository()
