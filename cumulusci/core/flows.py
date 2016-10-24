import copy
import logging
from cumulusci.core.utils import import_class

class BaseFlow(object):
    def __init__(self, project_config, flow_config, org_config):
        self.project_config = project_config
        self.flow_config = flow_config
        self.org_config = org_config
        self.responses = [] 
        self.tasks = []
        self._init_logger()
        self._init_flow()
    
    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.setLevel(logging.DEBUG)

    def _init_flow(self):
        self.logger.info(
            'Initializing flow class {} with config:\n{}'.format(
                self.__class__.__name__,
                self.flow_config,
            )
        )

    def __call__(self):
        
        for flow_task_config in self.flow_config.get('tasks',{}):
            self._run_task(flow_task_config)

    def _run_task(self, flow_task_config):
        task_config = self.project_config.get_task(flow_task_config['task'])
        task_config = copy.deepcopy(task_config)

        if flow_task_config:
            task_config['options'].update(flow_task_config.get('options', {}))

        task_class = import_class(task_config.get('class_path'))
        
        self.logger.info(
            'Initializing task {} using config:\n{}'.format(
                flow_task_config['task'], 
                task_config
            )
        )    

        task = task_class(
            self.project_config, 
            task_config, 
            org_config = self.org_config,
        )
        self.tasks.append(task)
        response = task()
        self.responses.append(response)
        return response
