import logging
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg

class BaseTask(object):
    task_options = {}
    salesforce_task = False  # Does this task require a salesforce org?

    def __init__(self, project_config, task_config, org_config=None, **kwargs):
        self.project_config = project_config
        self.task_config = task_config
        self.options = self.task_config.options
        if self.options is None:
            self.options = {}
        if kwargs:
            self.options.update(kwargs)
        self.org_config = org_config
        if self.salesforce_task and not self.org_config:
            raise TaskRequiresSalesforceOrg('This task requires a Saleforce org_config but none was passed to __init__')
        self._init_logger()
        self._init_task()

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def _init_task(self):
        """ A method that subclasses can override to implement dynamic logic for initializing the task """
        pass

    def __call__(self):
        return self._run_task()

    def _run_task(self):
        """ Subclasses should override to provide their implementation """
        pass
