""" Tests for the CumulusCI task module """

import unittest
import logging
import collections

from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.utils import MockLoggingHandler
import cumulusci.core


class _TaskHasResult(BaseTask):
    def _run_task(self):
        return -1


class TestBaseTaskCallable(unittest.TestCase):
    """ Tests for the BaseTask callable interface.

    BaseTask is Callable.
    Calling a BaseTask returns the return_values.
    Task results are available.
    """

    task_class = BaseTask

    @classmethod
    def setUpClass(cls):
        super(TestBaseTaskCallable, cls).setUpClass()
        logger = logging.getLogger(cumulusci.core.tasks.__name__)
        logger.setLevel(logging.DEBUG)
        cls._task_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._task_log_handler)

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.org_config = OrgConfig({
            'username': 'sample@example',
            'org_id': '00D000000000001'
        })
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_messages = self._task_log_handler.messages

    def test_task_is_callable(self):
        """ BaseTask is Callable """
        task = self.__class__.task_class(
            self.project_config,
            self.task_config,
            self.org_config
        )

        self.assertIsInstance(task, collections.Callable)

    def test_get_return_values(self):
        """ Callable interface returns retvals """

        class _TaskReturnsStuff(BaseTask):
            def _run_task(self):
                self.return_values['name'] = 'return!'

        task = _TaskReturnsStuff(
            self.project_config,
            self.task_config,
            self.org_config
        )
        return_values = task()

        self.assertIn('name', return_values)

    def test_get_task_result(self):
        """ Task results available as an instance member """

        task = _TaskHasResult(
            self.project_config,
            self.task_config,
            self.org_config
        )
        task()

        self.assertEqual(task.result, -1)

    def test_task_logs_name(self):
        """ A task logs the task class name to info """

        task = _TaskHasResult(
            self.project_config,
            self.task_config,
            self.org_config
        )

        task()

        task_name_logs = [log for
                          log in
                          self.task_messages['info'] if
                          '_TaskHasResult' in log]

        self.assertEquals(1, len(task_name_logs))
