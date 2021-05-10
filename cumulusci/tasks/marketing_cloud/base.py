from cumulusci.core.tasks import BaseTask


class BaseMarketingCloudTask(BaseTask):
    """Base task for interacting with Marketing Cloud

    For API calls to a MC tenant, you can get a fresh
    access token via the marketing cloud config like so:

    self.mc_config.access_token
    """

    def _init_task(self):
        super()._init_task()
        self.mc_config = self.project_config.keychain.get_service("marketing_cloud")
