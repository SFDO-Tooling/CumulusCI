""" Tests for the Flow engine """

import unittest
import logging
import mock

from collections import Callable

from cumulusci.core.flows import BaseFlow
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import FlowConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import FlowConfigError
from cumulusci.core.exceptions import FlowInfiniteLoopError
from cumulusci.core.exceptions import FlowNotReadyError
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.tests.utils import MockLoggingHandler
from cumulusci.tests.util import create_project_config
import cumulusci.core

ORG_ID = "00D000000000001"


class _TaskReturnsStuff(BaseTask):
    def _run_task(self):
        self.return_values = {"name": "supername"}


class _TaskResponseName(BaseTask):
    task_options = {"response": {"description": "the response to print"}}

    def _run_task(self):
        return self.options["response"]


class _TaskRaisesException(BaseTask):
    task_options = {
        "exception": {"description": "The exception to raise"},
        "message": {"description": "The exception message"},
    }

    def _run_task(self):
        raise self.options["exception"](self.options["message"])


class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1


@mock.patch("cumulusci.core.flows.BaseFlow._init_org")
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
        self.project_config = create_project_config("TestOwner", "TestRepo")
        self.project_config.config["tasks"] = {
            "pass_name": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flows._TaskReturnsStuff",
            },
            "name_response": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flows._TaskResponseName",
            },
            "raise_exception": {
                "description": "Raises an exception",
                "class_path": "cumulusci.core.tests.test_flows._TaskRaisesException",
                "options": {
                    "exception": Exception,
                    "message": "Test raised exception as expected",
                },
            },
            "sfdc_task": {
                "description": "An sfdc task",
                "class_path": "cumulusci.core.tests.test_flows._SfdcTask",
            },
        }
        self.project_config.config["flows"] = {
            "nested_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"task": "pass_name"}},
            },
            "nested_flow_2": {
                "description": "A flow that runs inside another flow, and calls another flow",
                "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
            },
        }
        self.org_config = OrgConfig(
            {"username": "sample@example", "org_id": ORG_ID}, "test"
        )

        self._flow_log_handler.reset()
        self.flow_log = self._flow_log_handler.messages

    def test_init(self, mock_class):
        """ BaseFlow initializes and offers a logger """
        flow_config = FlowConfig({})
        mock_class.return_value = None
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertEqual(hasattr(flow, "logger"), True)

    def test_is_callable(self, mock_class):
        """ BaseFlow exposes itself as a callable for use """
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        self.assertIsInstance(flow, Callable)

    def test_pass_around_values(self, mock_class):
        """ A flow's options reach into return values from other tasks. """

        mock_class.return_value = None
        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^pass_name.name"},
                    },
                },
            }
        )

        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        # run the flow
        flow()
        # the flow results for the second task should be 'name'
        self.assertEqual("supername", flow.step_results[1])

    def test_task_options(self, mock_class):
        """ A flow can accept task options and pass them to the task. """

        mock_class.return_value = None
        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "name_response", "options": {"response": "foo"}}},
            }
        )

        flow = BaseFlow(
            self.project_config,
            flow_config,
            self.org_config,
            options={"name_response__response": "bar"},
        )

        # run the flow
        flow()
        # the flow results for the first task should be 'bar'
        self.assertEqual("bar", flow.step_results[0])

    def test_skip_kwarg(self, mock_class):
        """ A flow can receive during init a list of tasks to skip """

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^pass_name.name"},
                    },
                },
            }
        )

        flow = BaseFlow(
            self.project_config, flow_config, self.org_config, skip=["name_response"]
        )

        # run the flow
        flow()

        # the number of tasks in the flow should be 1 instead of 2
        self.assertEqual(1, len(flow.step_results))

    def test_skip_task_value_none(self, mock_class):
        """ A flow skips any tasks whose name is None to allow override via yaml """

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "None"}},
            }
        )

        flow = BaseFlow(
            self.project_config, flow_config, self.org_config, skip=["name_response"]
        )

        # run the flow
        flow()

        # the number of tasks in the flow should be 1 instead of 2
        self.assertEqual(1, len(flow.step_results))

    def test_find_step_by_name_no_steps(self, mock_class):
        """ Running a flow with no steps throws an error """

        # instantiate a flow with two tasks
        flow_config = FlowConfig({"description": "Run two tasks"})

        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        self.assertIsNone(flow._find_step_by_name("task"))

        with self.assertRaises(FlowConfigError):
            flow()

    def test_find_step_by_name_not_first(self, mock_class):
        """ The _find_step_by_name method skips tasks that don't exist """

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^pass_name.name"},
                    },
                },
            }
        )

        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        flow()

        task = flow._find_step_by_name("name_response")
        self.assertEqual(
            "cumulusci.core.tests.test_flows._TaskResponseName",
            task.task_config.class_path,
        )

    def test_find_step_by_name__flow(self, mock_class):
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"flow": "nested_flow"},
                    2: {
                        "task": "name_response",
                        "options": {
                            "response": "^^nested_flow.pass_name.name",
                            "from_flow": "^^nested_flow.name",
                        },
                    },
                },
            }
        )

        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        flow()

        step = flow._find_step_by_name("nested_flow")
        self.assertIsInstance(step, BaseFlow)

    def test_render_task_config_empty_value(self, mock_class):
        """ The _render_task_config method skips option values of None """

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run a tasks",
                "steps": {1: {"task": "name_response", "options": {"response": None}}},
            }
        )

        flow = BaseFlow(self.project_config, flow_config, self.org_config)

        flow()

        task = flow._find_step_by_name("name_response")
        config = flow._render_task_config(task)
        self.assertEqual(["Options:"], config)

    def test_task_raises_exception_fail(self, mock_class):
        """ A flow aborts when a task raises an exception """

        flow_config = FlowConfig(
            {"description": "Run a task", "steps": {1: {"task": "raise_exception"}}}
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        self.assertRaises(Exception, flow)

    def test_task_raises_exception_ignore(self, mock_class):
        """ A flow continues when a task configured with ignore_failure raises an exception """

        flow_config = FlowConfig(
            {
                "description": "Run a task",
                "steps": {
                    1: {"task": "raise_exception", "ignore_failure": True},
                    2: {"task": "pass_name"},
                },
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()
        self.assertEqual(2, len(flow.steps))

    def test_call_no_tasks(self, mock_class):
        """ A flow with no tasks will have no responses. """
        flow_config = FlowConfig({"description": "Run no tasks", "steps": {}})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual([], flow.step_return_values)
        self.assertEqual([], flow.steps)

    def test_call_one_task(self, mock_class):
        """ A flow with one task will execute the task """
        flow_config = FlowConfig(
            {"description": "Run one task", "steps": {1: {"task": "pass_name"}}}
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertTrue(
            any("Flow Description: Run one task" in s for s in self.flow_log["info"])
        )

        self.assertEqual([{"name": "supername"}], flow.step_return_values)
        self.assertEqual(1, len(flow.steps))

    def test_call_many_tasks(self, mock_class):
        """ A flow with many tasks will dispatch each task """
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "pass_name"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        self.assertEqual(
            [{"name": "supername"}, {"name": "supername"}], flow.step_return_values
        )
        self.assertEqual(2, len(flow.steps))

    def test_call_task_not_found(self, mock_class):
        """ A flow with reference to a task that doesn't exist in the
        project will throw a TaskNotFoundError """

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "do_delightulthings"}},
            }
        )
        with self.assertRaises(TaskNotFoundError):
            flow = BaseFlow(self.project_config, flow_config, self.org_config)

    def test_flow_prints_org_id(self, mock_class):
        """ A flow with an org prints the org ID """

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "pass_name"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        org_id_logs = [s for s in self.flow_log["info"] if ORG_ID in s]

        self.assertEqual(1, len(org_id_logs))

    def test_flow_no_org_no_org_id(self, mock_class):
        """ A flow without an org does not print the org ID """

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "pass_name"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, None)
        flow()

        self.assertFalse(any(ORG_ID in s for s in self.flow_log["info"]))

    def test_flow_prints_org_id_once_only(self, mock_class):
        """ A flow with sf tasks prints the org ID only once."""

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "sfdc_task"}, 2: {"task": "sfdc_task"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()

        org_id_logs = [s for s in self.flow_log["info"] if ORG_ID in s]

        self.assertEqual(1, len(org_id_logs))

    def test_nested_flow(self, mock_class):
        """ Flows can run inside other flows """
        flow_config = FlowConfig(
            {
                "description": "Run a task and a flow",
                "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()
        self.assertEqual(2, len(flow.steps))
        self.assertEqual(flow.step_return_values[0], flow.step_return_values[1][0])

    def test_nested_flow_options(self, mock_class):
        flow_config = FlowConfig(
            {
                "description": "Run a flow with task options",
                "steps": {
                    1: {"flow": "nested_flow", "options": {"pass_name": {"foo": "bar"}}}
                },
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()
        self.assertEqual("bar", flow.steps[0].options["pass_name__foo"])

    def test_nested_flow_2(self, mock_class):
        """ Flows can run inside other flows and call other flows """
        flow_config = FlowConfig(
            {
                "description": "Run a task and a flow",
                "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow_2"}},
            }
        )
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        flow()
        self.assertEqual(2, len(flow.steps))
        self.assertEqual(flow.step_return_values[0], flow.step_return_values[1][0])
        self.assertEqual(flow.step_return_values[0], flow.step_return_values[1][1][0])

    def test_check_infinite_flows(self, mock_class):
        self.project_config.config["flows"] = {
            "nested_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"flow": "nested_flow"}},
            }
        }
        flow_config = FlowConfig({"steps": {1: {"flow": "nested_flow"}}})
        with self.assertRaises(FlowInfiniteLoopError):
            BaseFlow(self.project_config, flow_config, self.org_config)

    def test_rejects_old_syntax(self, mock_class):
        flow_config = FlowConfig({"tasks": {1: {"task": "pass_name"}}})
        flow = BaseFlow(self.project_config, flow_config, self.org_config)
        with self.assertRaises(FlowConfigError):
            flow._get_steps_ordered()

    def test_rejects_flow_and_task_in_same_step(self, mock_class):
        flow_config = FlowConfig(
            {"steps": {1: {"task": "pass_name", "flow": "nested_flow"}}}
        )
        with self.assertRaises(FlowConfigError):
            BaseFlow(self.project_config, flow_config, self.org_config)

    def test_call__not_prepped(self, mock_class):
        flow_config = FlowConfig({})
        flow = BaseFlow(self.project_config, flow_config, self.org_config, prep=False)
        with self.assertRaises(FlowNotReadyError):
            flow()
