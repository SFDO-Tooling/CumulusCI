import unittest
import logging
import mock

from cumulusci.core.flowrunner import FlowCoordinator
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


class TestFlowCoordinator(unittest.TestCase):
    """ Tests the expectations of a BaseFlow caller """

    @classmethod
    def setUpClass(cls):
        super(TestFlowCoordinator, cls).setUpClass()
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

    def test_init(self):
        flow_config = self.project_config.get_flow("nested_flow_2")
        flow = FlowCoordinator(self.project_config, flow_config, name="nested_flow_2")

        self.assertEqual(len(flow.steps), 2)

    #  @mock.patch("cumulusci.core.config.OrgConfig.refresh_oauth_token")
    #  def test_something_with_auth(self, refresh_token_mock):
    #      flow_config = self.project_config.get_flow('nested_flow')
    #      refresh_token_mock.return_value = None
