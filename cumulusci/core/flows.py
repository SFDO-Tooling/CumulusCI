import copy
from distutils.version import LooseVersion
import logging

from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import CumulusCIException
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
        self.logger = logging.getLogger(__name__)

    def _init_flow(self):
        self.logger.info('---------------------------------------')
        self.logger.info('Initializing flow class {}:'.format(
            self.__class__.__name__,
        ))
        self.logger.info('---------------------------------------')
        for line in self._render_config():
            self.logger.info(line)

    def _get_tasks(self):
        tasks = []
        for step_num, config in self.flow_config.tasks.items():
            if config['task'] == 'None':
                continue
            tasks.append((
                LooseVersion(str(step_num)),
                {
                    'flow_config': config,
                    'task_config': self.project_config.get_task(config['task']),
                }
            ))
        tasks.sort()
        tasks = [task_info[1] for task_info in tasks]
        return tasks

    def _render_config(self):
        config = []
        config.append('Flow Description: {}'.format(self.flow_config.description))

        if not self.flow_config.tasks:
            return config

        config.append('Tasks:')
        for task_info in self._get_tasks():
            config.append('  {}: {}'.format(
                task_info['flow_config']['task'],
                task_info['task_config'].description,
            ))

        return config

    def __call__(self):
        for flow_task_config in self._get_tasks():
            self._run_task(flow_task_config)

    def _find_task_by_name(self, name):
        if not self.flow_config.tasks:
            return

        i = 0
        for task in self._get_tasks():
            if task['flow_config']['task'] == name:
                if len(self.tasks) > i:
                    return self.tasks[i]
            i += 1

    def _run_task(self, flow_task_config):
        task_config = copy.deepcopy(flow_task_config['task_config'].config)
        task_config = TaskConfig(task_config)
    
        task_name = flow_task_config['flow_config']['task']

        if 'options' not in task_config.config:
            task_config.config['options'] = {}
        task_config.config['options'].update(flow_task_config['flow_config'].get('options', {}))

        # Handle dynamic value lookups in the format ^^task_name.attr1.attr2
        for option, value in task_config.options.items():
            if unicode(value).startswith('^^'):
                value_parts = value[2:].split('.')
                parent = self._find_task_by_name(value_parts[0])
                for attr in value_parts[1:]:
                    parent = getattr(parent, attr)
                task_config.config['options'][option] = parent


        task_class = import_class(task_config.class_path)

        self.logger.info('')
        self.logger.info(
            'Running task: {}'.format(task_name)
        )

        task = task_class(
            self.project_config,
            task_config,
            org_config = self.org_config,
        )
        self.tasks.append(task)

        for line in self._render_task_config(task):
            self.logger.info(line)

        try:
            response = task()
            self.logger.info('Task complete: {}'.format(task_name))
            self.responses.append(response)
            return response
        except Exception as e:
            self.logger.error('Task failed: {}'.format(task_name))
            if not flow_task_config['flow_config'].get('ignore_failure'):
                self.logger.error('Failing flow due to exception in task')
                raise
            self.logger.info('Continuing flow')

    def _render_task_config(self, task):
        config = ['Options:']
        if not task.task_options:
            return config

        for option_name, option_info in task.task_options.items():
            config.append('  {}: {}'.format(
                option_name,
                task.options.get(option_name),
            ))

        return config
