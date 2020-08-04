""" Tests for the CumulusCI task module """

import unittest
import collections
from unittest import mock

from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import UniversalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.exceptions import TaskRequiresSalesforceOrg
from cumulusci.core.tests.utils import MockLoggerMixin

ORG_ID = "00D000000000001"
USERNAME = "sample@example"


class _TaskHasResult(BaseTask):
    def _run_task(self):
        return -1


class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1


class TestBaseTaskCallable(MockLoggerMixin, unittest.TestCase):
    """ Tests for the BaseTask callable interface.

    BaseTask is a callable interface
    BaseTask has return_values and results
    BaseTask has basic logging
    """

    def setUp(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.org_config = OrgConfig({"username": USERNAME, "org_id": ORG_ID}, "test")
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    @mock.patch("cumulusci.core.tasks.time.sleep", mock.Mock())
    def test_retry_on_exception(self):
        """ calling _retry() should call try until the task succeeds.  """
        task_config = TaskConfig(
            {"options": {"retries": 5, "retry_interval": 1, "retry_interval_add": 1}}
        )
        task = BaseTask(self.project_config, task_config, self.org_config)
        task._try = mock.Mock(side_effect=[Exception, Exception, 1])
        task._retry()
        self.assertEqual(task._try.call_count, 3)

    @mock.patch("cumulusci.core.tasks.time.sleep", mock.Mock())
    def test_retry_until_too_many(self):
        """ calling _retry should call try until the retry count is exhausted. """
        task_config = TaskConfig(
            {"options": {"retries": 5, "retry_interval": 1, "retry_interval_add": 1}}
        )
        task = BaseTask(self.project_config, task_config, self.org_config)
        task._try = mock.Mock(
            side_effect=[
                RuntimeError(5),
                RuntimeError(4),
                RuntimeError(3),
                RuntimeError(2),
                RuntimeError(1),
                RuntimeError(0),
            ]
        )
        with self.assertRaises(RuntimeError) as cm:
            task._retry()
        self.assertEqual(cm.exception.args[0], 0)  # assert it was the final call
        self.assertEqual(task._try.call_count, 6)
        self.assertEqual(task.options["retry_interval"], 6)

    def test_task_is_callable(self):
        """ BaseTask is Callable """
        task = BaseTask(self.project_config, self.task_config, self.org_config)

        self.assertIsInstance(task, collections.abc.Callable)

    def test_option_overrides(self):
        task = BaseTask(
            self.project_config, self.task_config, self.org_config, foo="bar"
        )
        self.assertEqual("bar", task.options["foo"])

    def test_init_options__project_config_substitution(self):
        self.project_config.config["foo"] = {"bar": "baz"}
        self.task_config.config["options"] = {"test_option": "$project_config.foo__bar"}
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        self.assertEqual("baz", task.options["test_option"])

    def test_init_options__project_config_substitution__substring(self):
        self.project_config.config["foo"] = {"bar": "baz"}
        self.task_config.config["options"] = {
            "test_option": "before $project_config.foo__bar after"
        }
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        self.assertEqual("before baz after", task.options["test_option"])

    def test_validates_missing_options(self):
        class Task(BaseTask):
            task_options = {"test_option": {"required": True}}

        with self.assertRaises(TaskOptionsError):
            Task(self.project_config, self.task_config, self.org_config)

    def test_get_return_values(self):
        """ Callable interface returns retvals """

        class _TaskReturnsStuff(BaseTask):
            def _run_task(self):
                self.return_values["name"] = "return!"

        task = _TaskReturnsStuff(self.project_config, self.task_config, self.org_config)
        return_values = task()

        self.assertIn("name", return_values)

    def test_get_task_result(self):
        """ Task results available as an instance member """

        task = _TaskHasResult(self.project_config, self.task_config, self.org_config)
        task()

        self.assertEqual(task.result, -1)

    def test_task_logs_name_not_org(self):
        """ A task logs the task class name to info (and not creds) """

        task = _TaskHasResult(self.project_config, self.task_config, self.org_config)
        task()

        self.assertTrue(any("_TaskHasResult" in s for s in self.task_log["info"]))

        self.assertFalse(any(ORG_ID in s for s in self.task_log["info"]))

    def test_salesforce_task_logs_org_id(self):
        """ A salesforce_task will also log the org id & username """

        task = _SfdcTask(self.project_config, self.task_config, self.org_config)
        task()

        self.assertTrue(any(ORG_ID in s for s in self.task_log["info"]))

    def test_salesforce_task_no_org(self):
        with self.assertRaises(TaskRequiresSalesforceOrg):
            task = _SfdcTask(self.project_config, self.task_config)
            task()

    def test_no_id_if_run_from_flow(self):
        """ A salesforce_task will not log the org id if run from a flow """
        flow = mock.Mock()
        task = _SfdcTask(
            self.project_config, self.task_config, self.org_config, flow=flow
        )
        task()
        self.assertFalse(any(ORG_ID in s for s in self.task_log["info"]))

    def test_run_task(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with self.assertRaises(NotImplementedError):
            task()

    def test_try(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with self.assertRaises(NotImplementedError):
            task._try()

    def test_is_retry_valid(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        self.assertTrue(task._is_retry_valid(None))

    def test_poll_action(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with self.assertRaises(NotImplementedError):
            task._poll_action()

    @mock.patch("cumulusci.core.tasks.time.sleep", mock.Mock())
    def test_poll(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)

        task.i = 0

        def mimic_polling():
            task.i += 1
            if task.i > 3:
                task.poll_complete = True

        task._poll_action = mock.Mock(side_effect=mimic_polling)
        task._poll()
        self.assertEqual(4, task.poll_count)
        self.assertEqual(1, task.poll_interval_level)
        self.assertEqual(2, task.poll_interval_s)
