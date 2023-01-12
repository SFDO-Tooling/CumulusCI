from unittest import mock

from cumulusci.core.config import TaskConfig
from cumulusci.tasks.marketing_cloud.base import BaseMarketingCloudTask


class TestBaseMarketingCloudTask:
    def test_init(self, project_config):
        project_config.keychain.get_service = mock.Mock()
        task_config = TaskConfig({"options": {}})
        task = BaseMarketingCloudTask(project_config, task_config)
        task._init_task()

        assert task.mc_config is not None
