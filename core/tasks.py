import logging

class BaseTask(object):
    def __init__(self, project_config, task_config):
        self.project_config = project_config
        self.task_config = project_config
        self._init_logger()
        self._init_task()

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(self.__class__.__name__)

    def _init_task(self):
        """ A method that subclasses can override to implement dynamic logic for initializing the task """
        pass

    def __call__(self):
        raise NotImplementedError('Subclasses should provide their own implementation')
