import mock
import unittest

from cumulusci.core.exceptions import RobotTestFailure
from cumulusci.tasks.robotframework import Robot
from cumulusci.tasks.robotframework import RobotLibDoc
from cumulusci.tasks.robotframework import RobotTestDoc
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRobot(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    def test_run_task(self, robot_run):
        robot_run.return_value = 1
        task = create_task(Robot, {"suites": "tests", "pdb": True})
        with self.assertRaises(RobotTestFailure):
            task()


class TestRobotLibDoc(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.libdoc")
    def test_run_task(self, libdoc):
        task = create_task(RobotLibDoc, {"path": ".", "output": "out"})
        task()
        libdoc.assert_called_once_with(".", "out")


class TestRobotTestDoc(unittest.TestCase):
    @mock.patch("cumulusci.tasks.robotframework.robotframework.testdoc")
    def test_run_task(self, testdoc):
        task = create_task(RobotTestDoc, {"path": ".", "output": "out"})
        task()
        testdoc.assert_called_once_with(".", "out")
