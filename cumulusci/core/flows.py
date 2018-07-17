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
from cumulusci.core.exceptions import FlowConfigError
from cumulusci.core.exceptions import FlowInfiniteLoopError
from cumulusci.core.exceptions import FlowNotReadyError
from cumulusci.core.utils import import_class


class BaseFlow(object):
    """ BaseFlow handles initializing and running a flow """

    def __init__(
            self,
            project_config,
            flow_config,
            org_config,
            options=None,
            skip=None,
            nested=False,
            parent=None,
            prep=True,
            name=None,
            stepnum=None
    ):
        self.project_config = project_config # a subclass of BaseTaskFlowConfig, tho tasks may expect more than that
        self.flow_config = flow_config
        self.org_config = org_config
        self.options = options
        self.skip = skip
        self.task_options = {}
        self.skip_steps = []
        self.step_return_values = []  # A collection of return_values dicts in task execution order
        self.step_results = []  # A collection of result objects in task execution order
        self.steps = []  # A collection of configured task objects, either run or failed
        self.nested = nested  # indicates if flow is called from another flow
        self.parent = parent # parent flow, if nested
        self.name = name # the flows name.
        self.stepnum = stepnum # a nested flow has a stepnum
        self._skip_next = False # internal only control flow option for subclasses to override a step execution in their pre.
        self._init_options()
        self._init_skip(skip)
        self._init_logger()
        self.prepped = False
        if prep:
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
        for step in skip:
            self.skip_steps.append(step)

    def _init_logger(self):
        """ Initializes self.logger """
        self.logger = logging.getLogger(__name__)

    def _init_org(self):
        """ Refresh the token on the org """
        self.logger.info('Verifying and refreshing credentials for target org {}'.format(self.org_config.name))
        orig_config = self.org_config.config.copy()
        self.org_config.refresh_oauth_token(self.project_config.keychain)
        if self.org_config.config != orig_config:
            self.logger.info('Org info has changed, updating org in keychain')
            self.project_config.keychain.set_org(self.org_config)

    def _init_flow(self):
        """ Initialize the flow and print flow details to info """
        self.logger.info('---------------------------------------')
        if self.name:
            self.logger.info(
                'Initializing flow: {}'.format(self.name)
            )
        else:
            self.logger.info(
                'Initializing flow class: {}'.format(self.__class__.__name__)
            )
        self.logger.info('---------------------------------------')

        self.logger.info('')
        if not self.nested:
            self._init_org()
        for line in self._render_config():
            self.logger.info(line)
        self.prepped = True

    def _check_infinite_flows(self, steps, flows=None):
        if flows == None:
            flows = []
        for step in steps.values():
            if 'flow' in step:
                flow = step['flow']
                if flow in flows:
                    raise FlowInfiniteLoopError('Infinite flows detected with flow {}'.format(flow))
                flows.append(flow)
                flow_config = self.project_config.get_flow(flow)
                self._check_infinite_flows(flow_config.steps, flows)

    def _get_steps(self):
        steps = self._get_steps_ordered()
        steps = [step[1] for step in steps]  # drop the sort keys
        return steps

    def _get_steps_ordered(self):
        if self.flow_config.steps is None:
            if self.flow_config.tasks:
                raise FlowConfigError('Old flow syntax detected.  Please change from "tasks" to "steps" in the flow definition')
            else:
                raise FlowConfigError('No steps found in the flow definition')
        if not self.nested:
            self._check_infinite_flows(self.flow_config.steps)
        steps = []
        for step_num, config in list(self.flow_config.steps.items()):
            if 'flow' in config and 'task' in config:
                raise FlowConfigError('"flow" and "task" in same config item: {}'.format(config))
            if (('flow' in config and config['flow'] == 'None') or
                ('task' in config and config['task'] == 'None')):
                # allows skipping flows/tasks using YAML overrides
                continue
            parsed_step_num = LooseVersion(str(step_num))
            if 'flow' in config:  # nested flow
                flow_config = self.project_config.get_flow(config['flow'])
                steps.append((
                    parsed_step_num,
                    {
                        'step_config': config,
                        'flow_config': flow_config,
                    },
                ))
            elif 'task' in config:
                task_config = self.project_config.get_task(config['task'])
                steps.append((
                    parsed_step_num,
                    {
                        'step_config': config,
                        'task_config': task_config,
                    },
                ))
        steps.sort()  # sort by step number
        return steps

    def _render_config(self):
        config = []
        config.append(
            'Flow Description: {}'.format(self.flow_config.description)
        )

        if not self.flow_config.steps:
            return config

        config.append('Steps:')
        for step_config in self._get_steps():
            if 'flow_config' in step_config:
                step = step_config['step_config']['flow']
                flow_prefix = '(Flow) '
                description = step_config['flow_config'].description
            elif 'task_config' in step_config:
                step = step_config['step_config']['task']
                flow_prefix = ''
                description = step_config['task_config'].description

            config.append('  {}{}{}: {}'.format(
                '[SKIPPED] ' if step in self.skip_steps else '',
                flow_prefix,
                step,
                description,
            ))

        if self.org_config is not None:
            config.append('Organization:')
            config.append('  {}: {}'.format(
                'Username', self.org_config.username))
            config.append('  {}: {}'.format(
                '  Org Id', self.org_config.org_id))

        return config

    def __call__(self):
        if not self.nested:
            self._pre_flow()
        if not self.prepped:
            raise FlowNotReadyError('Flow executed before init_flow was called')
        for stepnum, step_config in self._get_steps_ordered():
            self._run_step(stepnum, step_config)
        if not self.nested:
            self._post_flow()

    def _pre_flow(self):
        pass
    
    def _post_flow(self):
        pass

    def _find_step_by_name(self, name):
        if not self.flow_config.steps:
            return

        i = 0
        for step in self._get_steps():
            if 'flow_config' in step:
                item = step['step_config']['flow']
            elif 'task_config' in step:
                item = step['step_config']['task']
            if item == name:
                if len(self.steps) > i:
                    return self.steps[i]
            i += 1

    def _run_step(self, stepnum, step_config):
        if 'flow_config' in step_config:
            self._run_flow(stepnum, step_config)
        elif 'task_config' in step_config:
            self._run_task(stepnum, step_config)

    def _run_flow(self, stepnum, step_config):
        class_path = step_config['flow_config'].config.get(
            'class_path',
            'cumulusci.core.flows.BaseFlow',
        )
        flow_options = step_config['step_config'].get(
            'options',
            {},
        )
        if flow_options:
            # Collapse down flow options into task__option format to pass
            options = {}
            for task, task_options in flow_options.items():
                for option, value in task_options.items():
                    options['{}__{}'.format(task, option)] = value
            flow_options = options
                
        flow_class = import_class(class_path)
        flow = flow_class(
            self.project_config,
            step_config['flow_config'],
            self.org_config,
            options=flow_options,
            skip=self.skip,
            nested=True,
            parent=self,
            name=step_config['step_config']['flow'],
            stepnum=stepnum
        )
        self._pre_subflow(flow)
        
        if self._skip_next:
            self._skip_next = False
            return

        flow()
        self._post_subflow(flow)
        self.steps.append(flow)
        self.step_return_values.append(flow.step_return_values)

    def _run_task(self, stepnum, step_config):

        task = self._get_task(stepnum, step_config)

        # Skip the task if skip was requested
        if task.name in self.skip_steps:
            self.logger.info('')
            self.logger.info('Skipping task {}'.format(task.name))
            return

        self.steps.append(task)

        for line in self._render_task_config(task):
            self.logger.info(line)

        # NOW TRY TO RUN THE TASK
        self.logger.info('')
        self.logger.info('Running task: %s', task.name)
        self._pre_task(task)
        if self._skip_next:
            self._skip_next = False
            return
        try:
            task()
            self.logger.info('Task complete: %s', task.name)
            self.step_results.append(task.result)
            self.step_return_values.append(task.return_values)
            self._post_task(task)
        except Exception as e:
            self._post_task_exception(task, e)
            self.logger.error('Task failed: %s', task.name)
            if not step_config['step_config'].get('ignore_failure'):
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

    def _pre_subflow(self, flow):
        pass

    def _post_subflow(self, flow):
        pass

    def _get_task(self, stepnum, step_config):
        task_config = copy.deepcopy(step_config['task_config'].config)
        task_config = TaskConfig(task_config)

        task_name = step_config['step_config']['task']

        if 'options' not in task_config.config:
            task_config.config['options'] = {}
        task_config.config['options'].update(
            step_config['step_config'].get('options', {})
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
                parent = self._find_step_by_name(value_parts[0])
                n = 0
                while isinstance(parent, BaseFlow):
                    n += 1
                    parent = parent._find_step_by_name(value_parts[n])
                for attr in value_parts[(n + 1):]:
                    if getattr(parent, 'nested', None):
                        parent = parent._find_step_by_name()
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
