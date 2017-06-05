""" The flow engine allows a series of tasks to be run. """

import copy
from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module
import logging
import traceback

from cumulusci.core.config import TaskConfig
from cumulusci.core.utils import import_class


class BaseFlow(object):
    """ BaseFlow handles initializing and running a flow """
    def __init__(self, project_config, flow_config, org_config, options=None, skip=None):
        self.project_config = project_config
        self.flow_config = flow_config
        self.org_config = org_config
        self.task_options = {}
        self.skip_tasks = []
        self.task_return_values = []
        """ A collection of return_values dicts in task execution order """
        self.task_results = []
        """ A collection of result objects in task execution order """
        self.tasks = []
        """ A collection of configured task objects, either run or failed """
        self._init_options(options)
        self._init_skip(skip)
        self._init_logger()
        self._init_flow()

    def _init_options(self, options):
        if not options:
            return
        for key, value in options.items():
            task, option = key.split('__')
            if task not in self.task_options:
                self.task_options[task] = {}
            self.task_options[task][option] = value
        
    def _init_skip(self, skip):
        if not skip:
            return
        for task in skip:
            self.skip_tasks.append(task)

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(__name__)

    def _init_flow(self):
        """ Initialize the flow and print flow details to info """
        self.logger.info('---------------------------------------')
        self.logger.info(
            'Initializing flow class %s:',
            self.__class__.__name__,
        )
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
                    'task_config': self.project_config.get_task(
                        config['task']
                    ),
                }
            ))
        tasks.sort()
        tasks = [task_info[1] for task_info in tasks]
        return tasks

    def _render_config(self):
        config = []
        config.append(
            'Flow Description: {}'.format(self.flow_config.description)
        )

        if not self.flow_config.tasks:
            return config

        config.append('Tasks:')
        for task_info in self._get_tasks():
            skipped = ''
            if task_info['flow_config']['task'] in self.skip_tasks:
                skipped = '[SKIPPED] '

            config.append('  {}{}: {}'.format(
                skipped,
                task_info['flow_config']['task'],
                task_info['task_config'].description,
            ))

        if self.org_config is not None:
            config.append('Organization:')
            config.append('  {}: {}'.format('Username', self.org_config.username))
            config.append('  {}: {}'.format('  Org Id', self.org_config.org_id))

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
        task_config.config['options'].update(
            flow_task_config['flow_config'].get('options', {})
        )
        # If there were task option overrides passed in, merge them
        if task_name in self.task_options:
            task_config.config['options'].update(
                self.task_options[task_name]
            )

        # Skip the task if skip was requested
        if task_name in self.skip_tasks:
            self.logger.info('')
            self.logger.info('Skipping task {}'.format(task_name))
            return

        # Handle dynamic value lookups in the format ^^task_name.attr1.attr2
        for option, value in task_config.options.items():
            if unicode(value).startswith('^^'):
                value_parts = value[2:].split('.')
                parent = self._find_task_by_name(value_parts[0])
                for attr in value_parts[1:]:
                    parent = parent.return_values.get(attr)
                task_config.config['options'][option] = parent

        task_class = import_class(task_config.class_path)

        self.logger.info('')
        self.logger.info('Running task: %s', task_name)

        task = task_class(
            self.project_config,
            task_config,
            org_config=self.org_config,
            flow=self
        )
        self.tasks.append(task)

        for line in self._render_task_config(task):
            self.logger.info(line)

        try:
            task()
            self.logger.info('Task complete: %s', task_name)
            self.task_results.append(task.result)
            self.task_return_values.append(task.return_values)
        except Exception as e:
            self.logger.error('Task failed: %s', task_name)
            if not flow_task_config['flow_config'].get('ignore_failure'):
                self.logger.error('Failing flow due to exception in task')
                traceback.print_exc()
                raise e
            self.logger.info('Continuing flow')

    def _render_task_config(self, task):
        config = ['Options:']
        if not task.task_options:
            return config
        for option, info in task.task_options.items():
            value = task.options.get(option)
            if value is None:
                continue
            config.append('  {}: {}'.format(
                option,
                value,
            ))

        return config
