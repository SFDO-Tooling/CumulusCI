""" Tests for the CumulusCI task module """

import unittest
import logging
import collections
import mock

from cumulusci.core.tasks import BaseTask
from cumulusci.core.flows import BaseFlow
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.config import FlowConfig
from cumulusci.core.tests.utils import MockLoggingHandler
import cumulusci.core

ORG_ID = '00D000000000001'
USERNAME = 'sample@example'


class _TaskHasResult(BaseTask):

    def _run_task(self):
        return -1


class _SfdcTask(BaseTask):
    salesforce_task = True

    def _run_task(self):
        return -1


class TestBaseTaskCallable(unittest.TestCase):
    """ Tests for the BaseTask callable interface.

    BaseTask is a callable interface
    BaseTask has return_values and results
    BaseTask has basic logging
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
            'username': USERNAME,
            'org_id': ORG_ID
        }, 'test')
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_task_is_callable(self):
        """ BaseTask is Callable """
        task = self.__class__.task_class(
            self.project_config,
            self.task_config,
            self.org_config
        )

        self.assertIsInstance(task, collections.Callable)

    def test_dynamic_options(self):
        """ Option values can lookup values from project_config """
        self.project_config.config['foo'] = {'bar': 'baz'}
        self.task_config.config['options'] = {
            'test_option': '$project_config.foo__bar',
        }
        task = self.__class__.task_class(
            self.project_config,
            self.task_config,
            self.org_config
        )
        self.assertEquals('baz', task.options['test_option'])

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

    def test_task_logs_name_not_org(self):
        """ A task logs the task class name to info (and not creds) """

        task = _TaskHasResult(
            self.project_config,
            self.task_config,
            self.org_config
        )
        task()

        self.assertTrue(any(
            "_TaskHasResult" in s for s in self.task_log['info']
        ))

        self.assertFalse(any(
            ORG_ID in s for s in self.task_log['info']
        ))

    def test_salesforce_task_logs_org_id(self):
        """ A salesforce_task will also log the org id & username """

        task = _SfdcTask(
            self.project_config,
            self.task_config,
            self.org_config
        )
        task()

        self.assertTrue(any(
            ORG_ID in s for s in self.task_log['info']
        ))

    @mock.patch('cumulusci.core.flows.BaseFlow._init_org')
    def test_no_id_if_run_from_flow(self, mock_class):
        """ A salesforce_task will not log the org id if run from a flow """

        mock_class.return_value = None
        task = _SfdcTask(
            self.project_config,
            self.task_config,
            self.org_config,
            flow=BaseFlow(self.project_config, FlowConfig(), self.org_config)
        )
        task()
        self.assertFalse(any(
            ORG_ID in s for s in self.task_log['info']
        ))
