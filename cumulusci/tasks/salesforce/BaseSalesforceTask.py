from cumulusci.core.tasks import BaseTask


class BaseSalesforceTask(BaseTask):
    name = 'BaseSalesforceTask'
    salesforce_task = True

    def _run_task(self):
        raise NotImplementedError(
            'Subclasses should provide their own implementation')

    def _update_credentials(self):
        orig_config = self.org_config.config.copy()
        self.org_config.refresh_oauth_token(self.project_config.keychain)
        if self.org_config.config != orig_config:
            self.logger.info('Org info updated, writing to keychain')
            self.project_config.keychain.set_org(self.org_config)
