""" Tests for the Flow engine """
from __future__ import unicode_literals

import unittest
import logging
import mock

from collections import Callable

from cumulusci.core.flows import BaseFlow
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.tests.utils import MockLoggingHandler
from cumulusci.tests.util import create_project_config
import cumulusci.core

ORG_ID = "00D000000000001"


class _TaskReturnsStuff(BaseTask):

    def _run_task(self):
        self.return_values = {'name': 'supername'}


class _TaskResponseName(BaseTask):
    task_options = {'response': {'description': 'the response to print'}}

    def _run_task(self):
        return self.options['response']

class _TaskRaisesException(BaseTask):
    task_options = {
        'exception': {'description': 'The exception to raise'},
        'message': {'description': 'The exception message'},
    }

    def _run_task(self):
        raise self.options['exception'](self.options['message'])

class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1

@mock.patch('cumulusci.core.flows.BaseFlow._init_org')
class TestBaseFlow(unittest.TestCase):
    """ Tests the expectations of a BaseFlow caller """

    @classmethod
    def setUpClass(cls):
        super(TestBaseFlow, cls).setUpClass()
        logger = logging.getLogger(cumulusci.core.__name__)
        logger.setLevel(logging.DEBUG)
        cls._flow_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._flow_log_handler)

    def setUp(self):
        self.project_config = create_project_config('TestOwner', 'TestRepo')
        self.project_config.config['tasks'] = {
            'pass_name': {
                'description': 'Pass the name',
                'class_path':
                    'cumulusci.core.tests.test_flows._TaskReturnsStuff',
            },
            'name_response': {
                'description': 'Pass the name',
                'class_path':
                    'cumulusci.core.tests.test_flows._TaskResponseName',
            },
            'raise_exception': {
                'description': 'Raises an exception',
                'class_path':
                    'cumulusci.core.tests.test_flows._TaskRaisesException',
                'options': {
                    'exception': Exception,
                    'message': 'Test raised exception as expected',
                }
            },
            'sfdc_task': {
                'description': 'An sfdc task',
                'class_path':
                    'cumulusci.core.tests.test_flows._SfdcTask'
            },
        }
        self.org_config = OrgConfig({
            'username': 'sample@example',
            'org_id': ORG_ID
        }, 'test')

        self._flow_log_handler.reset()
        self.flow_log = self._flow_log_handler.messages

    def test_init(self, mock_class):
        """ BaseFlow initializes and offers a logger """
        flow_config = FlowConfig({})
        mock_class.return_value = None
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertEquals(hasattr(flow, 'logger'), True)

    def test_is_callable(self, mock_class):
        """ BaseFlow exposes itself as a callable for use """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertIsInstance(flow, Callable)

    def test_pass_around_values(self, mock_class):
        """ A flow's options reach into return values from other tasks. """

        mock_class.return_value = None
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
        self.assertEquals('supername', flow.task_results[1])

    def test_task_options(self, mock_class):
        """ A flow can accept task options and pass them to the task. """

        mock_class.return_value = None
        # instantiate a flow with two tasks
        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'name_response', 'options': {
                    'response': 'foo'
                }},
            }
        })

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
            options={'name_response__response': 'bar'},
        )

        # run the flow
        flow()
        # the flow results for the first task should be 'bar'
        self.assertEquals('bar', flow.task_results[0])

    def test_skip_kwarg(self, mock_class):
        """ A flow can receive during init a list of tasks to skip """

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

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
            skip=['name_response'],
        )

        # run the flow
        flow()

        # the number of tasks in the flow should be 1 instead of 2
        self.assertEquals(1, len(flow.task_results))

    def test_skip_task_value_none(self, mock_class):
        """ A flow skips any tasks whose name is None to allow override via yaml """

        # instantiate a flow with two tasks
        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'None'},
            }
        })

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
            skip=['name_response'],
        )

        # run the flow
        flow()

        # the number of tasks in the flow should be 1 instead of 2
        self.assertEquals(1, len(flow.task_results))

    def test_find_task_by_name_no_tasks(self, mock_class):
        """ The _find_task_by_name method skips tasks that don't exist """

        # instantiate a flow with two tasks
        flow_config = FlowConfig({
            'description': 'Run two tasks',
        })

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
        )

        self.assertEquals(None, flow._find_task_by_name('missing'))

    def test_find_task_by_name_not_first(self, mock_class):
        """ The _find_task_by_name method skips tasks that don't exist """

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

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
        )

        flow()

        task = flow._find_task_by_name('name_response')
        self.assertEquals(
            'cumulusci.core.tests.test_flows._TaskResponseName',
            task.task_config.class_path,
        )

    def test_render_task_config_empty_value(self, mock_class):
        """ The _render_task_config method skips option values of None """

        # instantiate a flow with two tasks
        flow_config = FlowConfig({
            'description': 'Run a tasks',
            'tasks': {
                1: {'task': 'name_response',
                    'options': {
                        'response': None,
                    },
            
                   },
            },
        })

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
        )

        flow()

        task = flow._find_task_by_name('name_response')
        config = flow._render_task_config(task)
        self.assertEquals(['Options:'], config)

    def test_task_raises_exception_fail(self, mock_class):
        """ A flow aborts when a task raises an exception """

        flow_config = FlowConfig({
            'description': 'Run a task',
            'tasks': {
                1: {'task': 'raise_exception'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        self.assertRaises(Exception, flow)

    def test_task_raises_exception_ignore(self, mock_class):
        """ A flow continues when a task configured with ignore_failure raises an exception """

        flow_config = FlowConfig({
            'description': 'Run a task',
            'tasks': {
                1: {'task': 'raise_exception', 'ignore_failure': True},
                2: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()
        self.assertEquals(2, len(flow.tasks))

    def test_call_no_tasks(self, mock_class):
        """ A flow with no tasks will have no responses. """
        flow_config = FlowConfig({
            'description': 'Run no tasks',
            'tasks': {}
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual([], flow.task_return_values)
        self.assertEqual([], flow.tasks)

    def test_call_one_task(self, mock_class):
        """ A flow with one task will execute the task """
        flow_config = FlowConfig({
            'description': 'Run one task',
            'tasks': {
                1: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertTrue(any(
            "Flow Description: Run one task" in s for s in self.flow_log['info']
        ))

        self.assertEqual([{'name': 'supername'}], flow.task_return_values)
        self.assertEqual(1, len(flow.tasks))

    def test_call_many_tasks(self, mock_class):
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

        self.assertEqual(
            [{'name': 'supername'}, {'name': 'supername'}],
            flow.task_return_values
        )
        self.assertEqual(2, len(flow.tasks))

    def test_call_task_not_found(self, mock_class):
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

    def test_flow_prints_org_id(self, mock_class):
        """ A flow with an org prints the org ID """

        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        org_id_logs = [s for s in self.flow_log['info'] if ORG_ID in s]

        self.assertEqual(1, len(org_id_logs))

    def test_flow_no_org_no_org_id(self, mock_class):
        """ A flow without an org does not print the org ID """

        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'pass_name'},
                2: {'task': 'pass_name'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, None)
        flow()

        self.assertFalse(any(
            ORG_ID in s for s in self.flow_log['info']
        ))

    def test_flow_prints_org_id_once_only(self, mock_class):
        """ A flow with sf tasks prints the org ID only once."""

        flow_config = FlowConfig({
            'description': 'Run two tasks',
            'tasks': {
                1: {'task': 'sfdc_task'},
                2: {'task': 'sfdc_task'},
            }
        })
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        org_id_logs = [s for s in self.flow_log['info'] if ORG_ID in s]

        self.assertEqual(1, len(org_id_logs))
