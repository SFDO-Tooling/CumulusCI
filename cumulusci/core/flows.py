""" The flow engine allows a series of tasks to be run. """
from __future__ import unicode_literals

from builtins import str
from builtins import object
import copy
from distutils.version import LooseVersion  # pylint: disable=import-error,no-name-in-module
import logging
import traceback

from cumulusci.core.config import FlowConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.exceptions import ConfigError
from cumulusci.core.utils import import_class


class BaseFlow(object):
    """ BaseFlow handles initializing and running a flow """

    def __init__(self, project_config, flow_config, org_config, options=None, skip=None, nested=False):
        self.project_config = project_config
        self.flow_config = flow_config
        self.org_config = org_config
        self.options = options
        self.skip = skip
        self.task_options = {}
        self.skip_tasks = []
        self.task_return_values = []  # A collection of return_values dicts in task execution order
        self.task_results = []  # A collection of result objects in task execution order
        self.tasks = []  # A collection of configured task objects, either run or failed
        self.nested = nested  # indicates if flow is called from another flow
        self._init_options()
        self._init_skip(skip)
        self._init_logger()
        self._init_flow()

    def _init_options(self):
        if not self.options:
            return
        for key, value in list(self.options.items()):
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

    def _init_org(self):
        """ Refresh the token on the org """
        self.logger.info('Verifying and refreshing credentials for target org {}'.format(self.org_config.name))
        orig_config = self.org_config.config.copy()
        self.org_config.refresh_oauth_token(
            self.project_config.keychain.get_connected_app()
        )
        if self.org_config.config != orig_config:
            self.logger.info('Org info has changed, updating org in keychain')
            self.project_config.keychain.set_org(self.org_config)

    def _init_flow(self):
        """ Initialize the flow and print flow details to info """
        self.logger.info('---------------------------------------')
        self.logger.info(
            'Initializing flow class %s:',
            self.__class__.__name__,
        )
        self.logger.info('---------------------------------------')

        self.logger.info('')
        if not self.nested:
            self._init_org()
        for line in self._render_config():
            self.logger.info(line)

    def _check_infinite_flows(self, tasks, flows=None):
        if flows == None:
            flows = []
        for task in tasks.values():
            if 'flow' in task:
                flow = task['flow']
                if flow in flows:
                    raise ConfigError('Infinite flows detected')
                flows.append(flow)
                flow_config = self.project_config.get_flow(flow)
                self._check_infinite_flows(flow_config.tasks, flows)

    def _get_tasks(self):
        tasks = self._get_tasks_ordered()
        tasks = [task[1] for task in tasks]  # drop the sort keys
        return tasks

    def _get_tasks_ordered(self):
        if not self.nested:
            self._check_infinite_flows(self.flow_config.tasks)
        tasks = []
        for step_num, config in list(self.flow_config.tasks.items()):
            if 'flow' in config and 'task' in config:
                raise ConfigError('"flow" and "task" in same config item')
            if (('flow' in config and config['flow'] == 'None') or
                ('task' in config and config['task'] == 'None')):
                # allows skipping flows/tasks using YAML overrides
                continue
            if 'flow' in config:  # nested flow
                task_config = self.project_config.get_flow(config['flow'])
            elif 'task' in config:
                task_config = self.project_config.get_task(config['task'])
            tasks.append((
                LooseVersion(str(step_num)),
                {
                    'flow_config': config,
                    'task_config': task_config,
                }
            ))
        tasks.sort()  # sort by step number
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
            if 'flow' in task_info['flow_config']:
                task = task_info['flow_config']['flow']
                flow = '(Flow) '
            elif 'task' in task_info['flow_config']:
                task = task_info['flow_config']['task']
                flow = ''

            config.append('  {}{}{}: {}'.format(
                '[SKIPPED] ' if task in self.skip_tasks else '',
                flow,
                task,
                task_info['task_config'].description,
            ))

        if self.org_config is not None:
            config.append('Organization:')
            config.append('  {}: {}'.format(
                'Username', self.org_config.username))
            config.append('  {}: {}'.format(
                '  Org Id', self.org_config.org_id))

        return config

    def __call__(self):
        for stepnum, flow_task_config in self._get_tasks_ordered():
            self._run_step(stepnum, flow_task_config)

    def _find_task_by_name(self, name):
        if not self.flow_config.tasks:
            return

        i = 0
        for task in self._get_tasks():
            if 'flow' in task['flow_config']:
                item = task['flow_config']['flow']
            elif 'task' in task['flow_config']:
                item = task['flow_config']['task']
            if item == name:
                if len(self.tasks) > i:
                    return self.tasks[i]
            i += 1

    def _run_step(self, stepnum, flow_task_config):
        if isinstance(flow_task_config['task_config'], FlowConfig):
            self._run_flow(stepnum, flow_task_config)
        elif isinstance(flow_task_config['task_config'], TaskConfig):
            self._run_task(stepnum, flow_task_config)

    def _run_flow(self, stepnum, flow_task_config):
        class_path = flow_task_config['task_config'].config.get(
            'class_path',
            'cumulusci.core.flows.BaseFlow',
        )
        flow_class = import_class(class_path)
        flow = flow_class(
            self.project_config,
            flow_task_config['task_config'],
            self.org_config,
            options=self.options,
            skip=self.skip,
            nested=True,
        )
        flow()
        self.tasks.append(flow)
        self.task_return_values.append(flow.task_return_values)

    def _run_task(self, stepnum, flow_task_config):

        task = self._get_task(stepnum, flow_task_config)

        # Skip the task if skip was requested
        if task.name in self.skip_tasks:
            self.logger.info('')
            self.logger.info('Skipping task {}'.format(task.name))
            return

        self.tasks.append(task)

        for line in self._render_task_config(task):
            self.logger.info(line)

        # NOW TRY TO RUN THE TASK
        self.logger.info('')
        self.logger.info('Running task: %s', task.name)
        self._pre_task(task)
        try:
            task()
            self.logger.info('Task complete: %s', task.name)
            self.task_results.append(task.result)
            self.task_return_values.append(task.return_values)
            self._post_task(task)
        except Exception as e:
            self._post_task_exception(task, e)
            self.logger.error('Task failed: %s', task.name)
            if not flow_task_config['flow_config'].get('ignore_failure'):
                self.logger.error('Failing flow due to exception in task')
                traceback.print_exc()
                raise e
            self.logger.info('Continuing flow')

    def _pre_task(self, task):
        pass

    def _post_task(self, task):
        pass

    def _post_task_exception(self, task, exception):
        pass

    def _get_task(self, stepnum, flow_task_config):
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

        # Handle dynamic value lookups in the format ^^task_name.attr1.attr2
        for option, value in list(task_config.options.items()):
            if str(value).startswith('^^'):
                value_parts = value[2:].split('.')
                parent = self._find_task_by_name(value_parts[0])
                n = 0
                while isinstance(parent, BaseFlow):
                    n += 1
                    parent = parent._find_task_by_name(value_parts[n])
                for attr in value_parts[(n + 1):]:
                    if getattr(parent, 'nested', None):
                        parent = parent._find_task_by_name()
                    else:
                        parent = parent.return_values.get(attr)
                task_config.config['options'][option] = parent

        task_class = import_class(task_config.class_path)

        task = task_class(
            self.project_config,
            task_config,
            org_config=self.org_config,
            name = task_name,
            stepnum=stepnum,
            flow=self
        )
        return task


    def _render_task_config(self, task):
        config = ['Options:']
        if not task.task_options:
            return config
        for option, info in list(task.task_options.items()):
            value = task.options.get(option)
            if value is None:
                continue
            config.append('  {}: {}'.format(
                option,
                value,
            ))

        return config
