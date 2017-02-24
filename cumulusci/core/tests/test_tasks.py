""" Tests for the CumulusCI task module """

import unittest

import collections

from cumulusci.core.tasks import BaseTask
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig


class TestBaseTaskCallable(unittest.TestCase):
    """ Tests for the BaseTask callable interface.

    BaseTask is Callable.
    Calling a BaseTask returns the return_values.
    Task results are available.
    """

    task_class = BaseTask

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.org_config = OrgConfig({'foo': 'bar'})
        self.task_config = TaskConfig()

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

        class _TaskHasResult(BaseTask):
            def _run_task(self):
                return -1

        task = _TaskHasResult(
            self.project_config,
            self.task_config,
            self.org_config
        )
        task()

        self.assertEqual(task.result, -1)
