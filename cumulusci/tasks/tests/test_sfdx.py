""" Tests for the SFDX Command Wrapper"""

import unittest

import logging

from mock import MagicMock
from mock import patch

import cumulusci.core.tasks
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.config import OrgConfig
from cumulusci.core.keychain import BaseProjectKeychain
from cumulusci.core.tests.utils import MockLoggingHandler

from cumulusci.tasks.command import CommandException
from cumulusci.tasks.sfdx import SFDXBaseTask
from cumulusci.tasks.sfdx import SFDXOrgTask


class TestSFDXBaseTask(unittest.TestCase):
    """ Tests for the Base Task type """

    @classmethod
    def setUpClass(cls):
        super(TestSFDXBaseTask, cls).setUpClass()
        logger = logging.getLogger(cumulusci.core.tasks.__name__)
        logger.setLevel(logging.DEBUG)
        cls._task_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._task_log_handler)

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.task_config = TaskConfig()

        keychain = BaseProjectKeychain(self.project_config, '')
        self.project_config.set_keychain(keychain)

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_base_task(self):
        """ The command is prefixed w/ sfdx """

        self.task_config.config['options'] = {
            'command': 'force:org --help',
        }
        task = SFDXBaseTask(self.project_config, self.task_config)

        try:
            task()
        except CommandException:
            pass

        self.assertEqual('sfdx force:org --help', task.options['command'])

    @patch('cumulusci.tasks.sfdx.SFDXOrgTask._update_credentials',
           MagicMock(return_value=None))
    @patch('cumulusci.tasks.command.Command._run_task',
           MagicMock(return_value=None))
    def test_keychain_org_creds(self):
        """ Keychain org creds are passed by env var """

        self.task_config.config['options'] = {
            'command': 'force:org --help',
        }
        access_token = '00d123'
        org_config = OrgConfig({
            'access_token': access_token,
            'instance_url': 'https://test.salesforce.com'
        },'test')

        task = SFDXOrgTask(
            self.project_config, self.task_config, org_config
        )

        try:
            task()
        except CommandException:
            pass

        self.assertIn('SFDX_INSTANCE_URL', task._get_env())
        self.assertIn('SFDX_USERNAME', task._get_env())
        self.assertIn(access_token, task._get_env()['SFDX_USERNAME'])

    def test_scratch_org_username(self):
        """ Scratch Org credentials are passed by -u flag """

        self.task_config.config['options'] = {
            'command': 'force:org --help',
        }
        org_config = OrgConfig({
            'access_token': 'test access token',
            'instance_url': 'test instance url',
        }, 'test')

        task = SFDXOrgTask(
            self.project_config, self.task_config, org_config
        )

        try:
            task()
        except CommandException:
            pass

        env = task._get_env()
        print(env)
        self.assertEquals(env.get('SFDX_USERNAME'), 'test access token')
        self.assertEquals(env.get('SFDX_INSTANCE_URL'), 'test instance url')
