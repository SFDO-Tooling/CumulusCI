import mock
import unittest
import logging

import cumulusci
from cumulusci.core.exceptions import FlowConfigError
from cumulusci.core.exceptions import FlowInfiniteLoopError
from cumulusci.core.config import FlowConfig
from cumulusci.core.flowrunner import FlowCoordinator
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
            "test_flow": {
                "description": "A flow that calls another flow",
                "steps": {1: {"task": "pass_name"}, 2: {"flow": "nested_flow"}},
            },
        }

    def test_init(self):
        flow_config = self.project_config.get_flow("test_flow")
        flow = FlowCoordinator(self.project_config, flow_config, name="test_flow")

        self.assertEqual(len(flow.steps), 2)

    def test_init_ambiguous_step(self):
        flow_config = FlowConfig({"steps": {1: {"task": "None", "flow": "None"}}})
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_bad_classpath(self):
        self.project_config.config["tasks"] = {
            "classless": {
                "description": "Bogus class_path",
                "class_path": "this.is.not.a.thing",
            }
        }
        flow_config = FlowConfig(
            {
                "description": "A flow that skips its only step",
                "steps": {1: {"task": "classless"}},
            }
        )
        with self.assertRaises(FlowConfigError):
            FlowCoordinator(self.project_config, flow_config, name="test")

    def test_init_no_steps(self):
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

    def test_run_with_skip(self):
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
        org_config = mock.Mock()
        flow.run(org_config)
        callbacks.pre_task.assert_not_called()


class StepSpecTest(unittest.TestCase):
    def test_repr(self):
        spec = StepSpec(1, "test_task", {}, None, skip=True)
        assert "<!SKIP! StepSpec 1:test_task {}>" == repr(spec)

    def test_for_display(self):
        spec = StepSpec(1, "test_task", {}, None, skip=True)
        assert "1: test_task [SKIP]" == spec.for_display
