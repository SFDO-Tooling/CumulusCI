import logging

from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.exceptions import TaskOptionsError

class BaseTask(object):
    task_options = {}
    salesforce_task = False  # Does this task require a salesforce org?

    def __init__(self, project_config, task_config, org_config=None, **kwargs):
        self.project_config = project_config
        self.task_config = task_config
        self.org_config = org_config
        if self.salesforce_task and not self.org_config:
            raise TaskRequiresSalesforceOrg('This task requires a Saleforce org_config but none was passed to __init__')
        self._init_logger()
        self._init_options(kwargs)
        self._validate_options()
        self._update_credentials()
        self._init_task()

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(__name__)

    def _init_options(self, kwargs):
        """ Initializes self.options """
        self.options = self.task_config.options
        if self.options is None:
            self.options = {}
        if kwargs:
            self.options.update(kwargs)

    def _validate_options(self):
        missing_required = []
        for name, config in self.task_options.items():
            if config.get('required') == True and name not in self.options:
                missing_required.append(name)

        if missing_required:
            raise TaskOptionsError(
                'This task requires the options ({}) and no values were provided'.format(
                    ', '.join(missing_required)
                )
            )

    def _update_credentials(self):
        """ Subclasses should override to do any logic necessary to refresh credentials """
        pass

    def _init_task(self):
        """ A method that subclasses can override to implement dynamic logic for initializing the task """
        pass

    def __call__(self):
        res = self._run_task()
        return res
    
    def _run_task(self):
        """ Subclasses should override to provide their implementation """
        pass
