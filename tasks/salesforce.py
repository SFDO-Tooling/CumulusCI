import logging

from core.tasks import BaseTask
from salesforce_api.metadata import ApiDeploy
from salesforce_api.metadata import ApiRetrieveInstalledPackages
from salesforce_api.metadata import ApiRetrievePackaged
from salesforce_api.metadata import ApiRetrieveUnpackaged

class BaseSalesforceTask(BaseTask):
    name = 'BaseSalesforceTask'

    def __init__(self, project_config, task_config, org_config, **kwargs):
        self.org_config = org_config
        self.options = kwargs
        super(BaseSalesforceTask, self).__init__(project_config, task_config)

    def __call__(self):
        self._refresh_oauth_token()
        return self._run_task()

    def _run_task(self):
        raise NotImplementedError('Subclasses should provide their own implementation')

    def _refresh_oauth_token(self):
        self.org_config.refresh_oauth_token(self.project_config.keychain.app)

class BaseSalesforceMetadataApiTask(BaseSalesforceTask):
    api_class = None
    name = 'BaseSalesforceMetadataApiTask'
   
    def _run_task(self):
        api = self.api_class(self)
        if self.options:
            return api(**options)
        else:
            return api()

class GetInstalledPackages(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveInstalledPackages

class RetrieveUnpackaged(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrieveUnpackaged

class RetrievePackaged(BaseSalesforceMetadataApiTask):
    api_class = ApiRetrievePackaged

class Deploy(BaseSalesforceMetadataApiTask):
    api_class = ApiDeploy
