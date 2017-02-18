""" Tests for the Flow engine """

import unittest

from collections import Callable

from cumulusci.core.flows import BaseFlow
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig


class _TaskReturnsStuff(BaseTask):

    def _run_task(self):
        self.return_values = {'name': 'supername'}


class _TaskResponseName(BaseTask):
    task_options = {'response': {'description': 'the response to print'}}

    def _run_task(self):
        return self.options['response']


class TestBaseFlow(unittest.TestCase):
    """ Tests the expectations of a BaseFlow caller """

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.project_config.config['tasks'] = {
            'pass_name': {
                'description': 'Pass the name',
                'class_path': 'cumulusci.core.tests.test_flows._TaskReturnsStuff',
            },
            'name_response': {
                'description': 'Pass the name',
                'class_path': 'cumulusci.core.tests.test_flows._TaskResponseName',
            },
        }
        self.org_config = OrgConfig({'foo': 'bar'})

    def test_init(self):
        """ BaseFlow initializes and offers a logger """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertEquals(hasattr(flow, 'logger'), True)

    def test_is_callable(self):
        """ BaseFlow exposes itself as a callable for use """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertIsInstance(flow, Callable)

    def test_pass_around_values(self):
        """ A flow's options reach into return values from other tasks. """

        # instantiate a flow with two tasks
        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'name_response', 'options': {
                    'response': '^^pass_name.name'
                }},
            }
        })

        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        # run the flow
        flow()
        # the flow results for the second task should be 'name'
        self.assertEquals('supername', flow.tasks[1].result)

    def test_call_no_tasks(self):
        """ A flow with no tasks will have no responses. """
        flow_config = FlowConfig({
            'description': 'Run no tasks',
            'tasks': {}
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual([], flow.responses)
        self.assertEqual([], flow.tasks)

    def test_call_one_task(self):
        """ A flow with one task will execute the task """
        flow_config = FlowConfig({
            'description': 'Run one task',
            'tasks': {
                1: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual([{'name': 'supername'}], flow.responses)
        self.assertEqual(1, len(flow.tasks))

    def test_call_many_tasks(self):
        """ A flow with many tasks will dispatch each task """
        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual([{'name': 'supername'}, {'name': 'supername'}], flow.responses)
        self.assertEqual(2, len(flow.tasks))

    def test_call_task_not_found(self):
        """ A flow with reference to a task that doesn't exist in the
        project will throw an AttributeError """

        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'do_delightulthings'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertRaises(AttributeError, flow)
