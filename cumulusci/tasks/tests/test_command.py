""" Tests for the Command tasks """

import unittest
import logging

from testfixtures.popen import MockPopen
from testfixtures import Replacer

import cumulusci.core.tasks
from cumulusci.core.config import BaseGlobalConfig
from cumulusci.core.config import BaseProjectConfig
from cumulusci.core.config import TaskConfig
from cumulusci.core.tests.utils import MockLoggingHandler

from cumulusci.tasks.command import Command
from cumulusci.tasks.command import CommandException


class TestCommandTask(unittest.TestCase):
    """ Tests for the basic command task """

    @classmethod
    def setUpClass(cls):
        super(TestCommandTask, cls).setUpClass()
        logger = logging.getLogger(cumulusci.core.tasks.__name__)
        logger.setLevel(logging.DEBUG)
        cls._task_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._task_log_handler)

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.task_config = TaskConfig()
        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_functional_run_ls(self):
        """ Functional test that actually subprocesses and runs command.

        Checks that command either ran successfully or failed as expected
        so that it can be run on any platform. Other tests will mock
        the subprocess interaction.
        """

        self.task_config.config['options'] = {
            'command': 'ls -la',
        }

        task = Command(self.project_config, self.task_config)

        # try to run the command and handle the command Exception
        # if no exception, confirm that we logged
        # if exception, confirm exception matches expectations
        try:
            task()
        except CommandException:
            self.assertTrue(any(
                "Return code" in s for s in self.task_log['error']
            ))

        self.assertTrue(any(
            "total" in s for s in self.task_log['info']
        ))


class TestCommandTaskWithMockPopen(unittest.TestCase):
    """ Run command tasks with a mocked popen """

    @classmethod
    def setUpClass(cls):
        super(TestCommandTaskWithMockPopen, cls).setUpClass()
        logger = logging.getLogger(cumulusci.core.tasks.__name__)
        logger.setLevel(logging.DEBUG)
        cls._task_log_handler = MockLoggingHandler(logging.DEBUG)
        logger.addHandler(cls._task_log_handler)

    def setUp(self):
        self.global_config = BaseGlobalConfig()
        self.project_config = BaseProjectConfig(self.global_config)
        self.task_config = TaskConfig()

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

        self.Popen = MockPopen()
        self.r = Replacer()
        self.r.replace('cumulusci.tasks.command.subprocess.Popen', self.Popen)
        self.addCleanup(self.r.restore)

    def test_functional_mock_command(self):
        """ Functional test that runs a command with mocked
        popen results and checks the log.
        """

        self.task_config.config['options'] = {
            'command': 'ls -la',
        }

        self.Popen.set_command(
            'ls -la',
            stdout=b'testing testing 123',
            stderr=b'e'
        )

        task = Command(self.project_config, self.task_config)
        task()

        self.assertTrue(any(
            "testing testing" in s for s in self.task_log['info']
        ))
