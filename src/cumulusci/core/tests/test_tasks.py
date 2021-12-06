""" Tests for the CumulusCI task module """

import collections
import logging
from unittest import mock

import pytest

from cumulusci.core.config import (
    BaseProjectConfig,
    OrgConfig,
    TaskConfig,
    UniversalConfig,
)
from cumulusci.core.exceptions import TaskOptionsError, TaskRequiresSalesforceOrg
from cumulusci.core.tasks import BaseTask

ORG_ID = "00D000000000001"
USERNAME = "sample@example"


class _TaskHasResult(BaseTask):
    def _run_task(self):
        return -1


class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1


class _TaskWithOutput(BaseTask):
    def _run_task(self):
        print("1", end="")
        print("2")


class TestBaseTaskCallable:
    """Tests for the BaseTask callable interface.

    BaseTask is a callable interface
    BaseTask has return_values and results
    BaseTask has basic logging
    """

    def setup_method(self, method):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config, config={"noyaml": True}
        )
        self.org_config = OrgConfig({"username": USERNAME, "org_id": ORG_ID}, "test")
        self.task_config = TaskConfig()

    @mock.patch("cumulusci.core.tasks.time.sleep", mock.Mock())
    def test_retry_on_exception(self):
        """calling _retry() should call try until the task succeeds."""
        task_config = TaskConfig(
            {"options": {"retries": 5, "retry_interval": 1, "retry_interval_add": 1}}
        )
        task = BaseTask(self.project_config, task_config, self.org_config)
        task._try = mock.Mock(side_effect=[Exception, Exception, 1])
        task._retry()
        assert task._try.call_count == 3

    @mock.patch("cumulusci.core.tasks.time.sleep", mock.Mock())
    def test_retry_until_too_many(self):
        """calling _retry should call try until the retry count is exhausted."""
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
        with pytest.raises(RuntimeError) as exc_info:
            task._retry()
        assert exc_info.value.args[0] == 0  # assert it was the final call
        assert task._try.call_count == 6
        assert task.options["retry_interval"] == 6

    def test_task_is_callable(self):
        """BaseTask is Callable"""
        task = BaseTask(self.project_config, self.task_config, self.org_config)

        assert isinstance(task, collections.abc.Callable)

    def test_option_overrides(self):
        task = BaseTask(
            self.project_config, self.task_config, self.org_config, foo="bar"
        )
        assert task.options["foo"] == "bar"

    def test_init_options__project_config_substitution(self):
        self.project_config.config["foo"] = {"bar": "baz"}
        self.task_config.config["options"] = {"test_option": "$project_config.foo__bar"}
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        assert task.options["test_option"] == "baz"

    def test_init_options__not_shared(self):
        self.project_config.config["foo"] = {"bar": "baz"}
        self.task_config.config["options"] = {}
        task1 = BaseTask(self.project_config, self.task_config, self.org_config)
        self.task_config.options["test_option"] = "baz"
        task1._init_options({})
        self.task_config.options["test_option"] = "jazz"
        task2 = BaseTask(self.project_config, self.task_config, self.org_config)
        task2._init_options({})
        assert task1.options["test_option"] == "baz"
        assert task2.options["test_option"] == "jazz"

    def test_init_options__project_config_integer(self):
        self.project_config.config["foo"] = {"bar": 32}
        self.task_config.config["options"] = {"test_option": "$project_config.foo__bar"}
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        assert task.options["test_option"] == "32"

    def test_init_options__project_config_substitution__substring(self):
        self.project_config.config["foo"] = {"bar": "baz"}
        self.task_config.config["options"] = {
            "test_option": "before $project_config.foo__bar after"
        }
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        assert task.options["test_option"] == "before baz after"

    def test_validates_missing_options(self):
        class Task(BaseTask):
            task_options = {"test_option": {"required": True}}

        with pytest.raises(TaskOptionsError):
            Task(self.project_config, self.task_config, self.org_config)

    def test_get_return_values(self):
        """Callable interface returns retvals"""

        class _TaskReturnsStuff(BaseTask):
            def _run_task(self):
                self.return_values["name"] = "return!"

        task = _TaskReturnsStuff(self.project_config, self.task_config, self.org_config)
        return_values = task()

        assert "name" in return_values

    def test_get_task_result(self):
        """Task results available as an instance member"""

        task = _TaskHasResult(self.project_config, self.task_config, self.org_config)
        task()

        assert task.result == -1

    def test_task_logs_name_not_org(self, caplog):
        """A task logs the task class name to info (and not creds)"""
        caplog.set_level(logging.INFO)

        task = _TaskHasResult(self.project_config, self.task_config, self.org_config)
        task()

        assert "_TaskHasResult" in caplog.text
        assert ORG_ID not in caplog.text

    def test_salesforce_task_logs_org_id(self, caplog):
        """A salesforce_task will also log the org id & username"""
        caplog.set_level(logging.INFO)

        task = _SfdcTask(self.project_config, self.task_config, self.org_config)
        task()

        assert ORG_ID in caplog.text

    def test_salesforce_task_no_org(self):
        with pytest.raises(TaskRequiresSalesforceOrg):
            task = _SfdcTask(self.project_config, self.task_config)
            task()

    def test_no_id_if_run_from_flow(self, caplog):
        """A salesforce_task will not log the org id if run from a flow"""
        flow = mock.Mock()
        task = _SfdcTask(
            self.project_config, self.task_config, self.org_config, flow=flow
        )
        task()
        assert ORG_ID not in caplog.text

    def test_run_task(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with pytest.raises(NotImplementedError):
            task()

    def test_try(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with pytest.raises(NotImplementedError):
            task._try()

    def test_is_retry_valid(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        assert task._is_retry_valid(None)

    def test_poll_action(self):
        task = BaseTask(self.project_config, self.task_config, self.org_config)
        with pytest.raises(NotImplementedError):
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
        assert task.poll_count == 4
        assert task.poll_interval_level == 1
        assert task.poll_interval_s == 2

    def test_explicit_logger(self):
        """Verify that the logger is properly set when passed in as an argument"""
        mock_logger = mock.Mock()
        task = BaseTask(
            self.project_config, self.task_config, self.org_config, logger=mock_logger
        )
        assert task.logger is mock_logger

    def test_task_captures_output(self, caplog, capsys):
        caplog.set_level(logging.INFO)
        with mock.patch("cumulusci.core.tasks.CAPTURE_TASK_OUTPUT", True):
            task = _TaskWithOutput(
                self.project_config, self.task_config, self.org_config
            )
            task()
        assert "12" not in capsys.readouterr().out
        assert "12" in caplog.text
