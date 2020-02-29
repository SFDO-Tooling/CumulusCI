from unittest import mock
import unittest
import logging

import cumulusci
from cumulusci.core.exceptions import FlowConfigError
from cumulusci.core.exceptions import FlowInfiniteLoopError
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.core.config import FlowConfig
from cumulusci.core.flowrunner import FlowCoordinator
from cumulusci.core.flowrunner import PreflightFlowCoordinator
from cumulusci.core.flowrunner import StepSpec
from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import OrgConfig
from cumulusci.core.tests.utils import MockLoggingHandler
from cumulusci.tests.util import create_project_config

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


class AbstractFlowCoordinatorTest(object):
    @classmethod
    def setUpClass(cls):
        super(AbstractFlowCoordinatorTest, cls).setUpClass()
        logger = logging.getLogger(cumulusci.__name__)
        logger.setLevel(logging.DEBUG)
        cls._flow_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._flow_log_handler)

    def setUp(self):
        self.project_config = create_project_config("TestOwner", "TestRepo")
        self.org_config = OrgConfig(
            {"username": "sample@example", "org_id": ORG_ID}, "test"
        )
        self.org_config.refresh_oauth_token = mock.Mock()

        self._flow_log_handler.reset()
        self.flow_log = self._flow_log_handler.messages
        self._setup_project_config()

    def _setup_project_config(self):
        pass


class FullParseTestFlowCoordinator(AbstractFlowCoordinatorTest, unittest.TestCase):
    def test_each_flow(self):
        for flow_name in [
            flow_info["name"] for flow_info in self.project_config.list_flows()
        ]:
            try:
                flow_config = self.project_config.get_flow(flow_name)
                flow = FlowCoordinator(self.project_config, flow_config, name=flow_name)
            except Exception as exc:
                self.fail("Error creating flow {}: {}".format(flow_name, str(exc)))
            self.assertIsNotNone(
                flow.steps, "Flow {} parsed to no steps".format(flow_name)
            )
            print("Parsed flow {} as {} steps".format(flow_name, len(flow.steps)))


class SimpleTestFlowCoordinator(AbstractFlowCoordinatorTest, unittest.TestCase):
    """ Tests the expectations of a BaseFlow caller """

    def _setup_project_config(self):
        self.project_config.config["tasks"] = {
            "pass_name": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskReturnsStuff",
            },
            "name_response": {
                "description": "Pass the name",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskResponseName",
            },
            "raise_exception": {
                "description": "Raises an exception",
                "class_path": "cumulusci.core.tests.test_flowrunner._TaskRaisesException",
                "options": {
                    "exception": Exception,
                    "message": "Test raised exception as expected",
                },
            },
            "sfdc_task": {
                "description": "An sfdc task",
                "class_path": "cumulusci.core.tests.test_flowrunner._SfdcTask",
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

    def test_init(self):
        flow_config = FlowConfig({"steps": {"1": {"task": "pass_name"}}})
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")

        self.assertEqual(len(flow.steps), 1)
        self.assertEqual(hasattr(flow, "logger"), True)

    def test_get_summary(self):
        self.project_config.config["flows"]["test"] = {
            "description": "test description",
            "steps": {"1": {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")
        actual_output = flow.get_summary()
        expected_output = (
            "Description: test description"
            + "\n1) flow: nested_flow_2 [from current folder]"
            + "\n    1) task: pass_name"
            + "\n    2) flow: nested_flow"
            + "\n        1) task: pass_name"
        )
        self.assertEqual(expected_output, actual_output)

    def test_get_summary__substeps(self):
        flow = FlowCoordinator.from_steps(
            self.project_config,
            [StepSpec("1", "test", {}, None, self.project_config, from_flow="test")],
        )
        assert flow.get_summary() == ""

    def test_get_summary__multiple_sources(self):
        other_project_config = mock.MagicMock()
        other_project_config.source.__str__.return_value = "other source"
        flow = FlowCoordinator.from_steps(
            self.project_config,
            [
                StepSpec(
                    "1/1",
                    "other:test1",
                    {},
                    None,
                    other_project_config,
                    from_flow="test",
                ),
                StepSpec(
                    "1/2", "test2", {}, None, self.project_config, from_flow="test"
                ),
            ],
        )
        assert (
            "1) flow: test"
            + "\n    1) task: other:test1 [from other source]"
            + "\n    2) task: test2 [from current folder]"
        ) == flow.get_summary()

    def test_init__options(self):
        """ A flow can accept task options and pass them to the task. """

        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "name_response", "options": {"response": "foo"}}},
            }
        )

        flow = FlowCoordinator(
            self.project_config,
            flow_config,
            options={"name_response": {"response": "bar"}},
        )

        # the first step should have the option
        self.assertEqual("bar", flow.steps[0].task_config["options"]["response"])

    def test_init__nested_options(self):
        self.project_config.config["flows"]["test"] = {
            "description": "Run a flow with task options",
            "steps": {
                1: {"flow": "nested_flow", "options": {"pass_name": {"foo": "bar"}}}
            },
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        self.assertEqual("bar", flow.steps[0].task_config["options"]["foo"])

    def test_init_ambiguous_step(self):
        flow_config = FlowConfig({"steps": {1: {"task": "None", "flow": "None"}}})
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init__bad_classpath(self):
        self.project_config.config["tasks"] = {
            "classless": {
                "description": "Bogus class_path",
                "class_path": "this.is.not.a.thing",
            }
        }
        flow_config = FlowConfig(
            {
                "description": "A flow with a broken task",
                "steps": {1: {"task": "classless"}},
            }
        )
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init__task_not_found(self):
        """ A flow with reference to a task that doesn't exist in the
        project will throw a TaskNotFoundError """

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "do_delightulthings"}},
            }
        )
        with self.assertRaises(TaskNotFoundError):
            FlowCoordinator(self.project_config, flow_config)

    def test_init__no_steps_in_config(self):
        flow_config = FlowConfig({})
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_old_format(self):
        flow_config = FlowConfig({"tasks": {}})
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_recursive_flow(self):
        self.project_config.config["flows"] = {
            "self_referential_flow": {
                "description": "A flow that runs inside another flow",
                "steps": {1: {"flow": "self_referential_flow"}},
            }
        }
        flow_config = self.project_config.get_flow("self_referential_flow")
        with self.assertRaises(FlowInfiniteLoopError):
            FlowCoordinator(
                self.project_config, flow_config, name="self_referential_flow"
            )

    def test_from_steps(self):
        steps = [StepSpec("1", "test", {}, _TaskReturnsStuff, None)]
        flow = FlowCoordinator.from_steps(self.project_config, steps)
        self.assertEqual(1, len(flow.steps))

    def test_run__one_task(self):
        """ A flow with one task will execute the task """
        flow_config = FlowConfig(
            {"description": "Run one task", "steps": {1: {"task": "pass_name"}}}
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        self.assertEqual(1, len(flow.steps))

        flow.run(self.org_config)

        self.assertTrue(
            any(flow_config.description in s for s in self.flow_log["info"])
        )
        self.assertEqual({"name": "supername"}, flow.results[0].return_values)

    def test_run__nested_flow(self):
        """ Flows can run inside other flows """
        self.project_config.config["flows"]["test"] = {
            "description": "Run a task and a flow",
            "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        self.assertEqual(2, len(flow.steps))
        self.assertEqual(flow.results[0].return_values, flow.results[1].return_values)

    def test_run__nested_flow_2(self):
        """ Flows can run inside other flows and call other flows """
        self.project_config.config["flows"]["test"] = {
            "description": "Run a task and a flow",
            "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow_2"}},
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        self.assertEqual(3, len(flow.steps))
        self.assertEqual(flow.results[0].return_values, flow.results[1].return_values)
        self.assertEqual(flow.results[1].return_values, flow.results[2].return_values)

    def test_run__option_backrefs(self):
        """ A flow's options reach into return values from other tasks. """

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

        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        # the flow results for the second task should be 'name'
        self.assertEqual("supername", flow.results[1].result)

    def test_run__option_backref_not_found(self):
        # instantiate a flow with two tasks
        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {
                    1: {"task": "pass_name"},
                    2: {
                        "task": "name_response",
                        "options": {"response": "^^bogus.name"},
                    },
                },
            }
        )

        flow = FlowCoordinator(self.project_config, flow_config)
        with self.assertRaises(NameError):
            flow.run(self.org_config)

    def test_run__nested_option_backrefs(self):
        self.project_config.config["flows"]["test"] = {
            "description": "Run two tasks",
            "steps": {
                1: {"flow": "nested_flow"},
                2: {
                    "task": "name_response",
                    "options": {"response": "^^nested_flow.pass_name.name"},
                },
            },
        }
        flow_config = self.project_config.get_flow("test")
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        self.assertEqual("supername", flow.results[-1].result)

    def test_run__skip_flow_None(self):
        flow_config = FlowConfig(
            {
                "description": "A flow that skips its only step",
                "steps": {1: {"task": "None"}},
            }
        )
        callbacks = mock.Mock()
        flow = FlowCoordinator(
            self.project_config, flow_config, name="skip", callbacks=callbacks
        )
        flow.run(self.org_config)
        callbacks.pre_task.assert_not_called()

    def test_run__skip_from_init(self):
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
        flow = FlowCoordinator(self.project_config, flow_config, skip=["name_response"])
        flow.run(self.org_config)

        # the number of results should be 1 instead of 2
        self.assertEqual(1, len(flow.results))

    def test_run__skip_conditional_step(self):
        flow_config = FlowConfig({"steps": {1: {"task": "pass_name", "when": "False"}}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        assert len(flow.results) == 0

    def test_run__task_raises_exception_fail(self):
        """ A flow aborts when a task raises an exception """

        flow_config = FlowConfig(
            {"description": "Run a task", "steps": {1: {"task": "raise_exception"}}}
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        with self.assertRaises(Exception):
            flow.run(self.org_config)

    def test_run__task_raises_exception_ignore(self):
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
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)
        self.assertEqual(2, len(flow.results))
        self.assertIsNotNone(flow.results[0].exception)

    def test_run__no_steps(self):
        """ A flow with no tasks will have no results. """
        flow_config = FlowConfig({"description": "Run no tasks", "steps": {}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        self.assertEqual([], flow.steps)
        self.assertEqual([], flow.results)

    def test_run__prints_org_id(self):
        """ A flow with an org prints the org ID """

        flow_config = FlowConfig(
            {
                "description": "Run two tasks",
                "steps": {1: {"task": "pass_name"}, 2: {"task": "sfdc_task"}},
            }
        )
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        org_id_logs = [s for s in self.flow_log["info"] if ORG_ID in s]

        self.assertEqual(1, len(org_id_logs))

    def test_init_org_updates_keychain(self):
        self.project_config.keychain.set_org = set_org = mock.Mock()

        def change_username(keychain):
            self.org_config.config["username"] = "sample2@example"

        self.org_config.refresh_oauth_token = change_username

        flow_config = FlowConfig({"steps": {1: {"task": "pass_name"}}})
        flow = FlowCoordinator(self.project_config, flow_config)
        flow.org_config = self.org_config
        flow._init_org()

        set_org.assert_called_once()


class StepSpecTest(unittest.TestCase):
    def test_repr(self):
        spec = StepSpec(1, "test_task", {}, None, None, skip=True)
        assert "<!SKIP! StepSpec 1:test_task {}>" == repr(spec)


class PreflightFlowCoordinatorTest(AbstractFlowCoordinatorTest, unittest.TestCase):
    def test_run(self):
        flow_config = FlowConfig(
            {
                "checks": [
                    {"when": "True", "action": "error", "message": "Failed plan check"}
                ],
                "steps": {
                    1: {
                        "task": "log",
                        "options": {"level": "info", "line": "step"},
                        "checks": [
                            {
                                "when": "tasks.log(level='info', line='plan')",
                                "action": "error",
                                "message": "Failed step check 1",
                            },
                            {
                                "when": "not tasks.log(level='info', line='plan')",
                                "action": "error",
                                "message": "Failed step check 2",
                            },
                        ],
                    }
                },
            }
        )
        flow = PreflightFlowCoordinator(self.project_config, flow_config)
        flow.run(self.org_config)

        self.assertDictEqual(
            {
                None: [{"status": "error", "message": "Failed plan check"}],
                "1": [{"status": "error", "message": "Failed step check 2"}],
            },
            flow.preflight_results,
        )
        # Make sure task result got cached
        key = ("log", (("level", "info"), ("line", "plan")))
        assert key in flow._task_cache.results
