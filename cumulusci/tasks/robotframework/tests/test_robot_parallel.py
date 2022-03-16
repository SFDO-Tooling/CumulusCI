"""
Tests for the robot task, specifically for options related to running tests in parallel
"""

import sys
from pathlib import Path
from unittest import mock

from cumulusci.tasks.robotframework import Robot
from cumulusci.tasks.salesforce.tests.util import create_task


class TestRobotParallel:
    """Tests for the robot task when running tests with pabot"""

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_process_arg_gt_zero(self, mock_subprocess_run, mock_robot_run):
        """Verify that setting the process option to a number > 1 runs pabot"""
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        task = create_task(Robot, {"suites": "tests", "processes": "2"})
        task()
        outputdir = str(Path(".").resolve())
        expected_cmd = [
            sys.executable,
            "-m",
            "pabot.pabot",
            "--pabotlib",
            "--processes",
            "2",
            "--pythonpath",
            task.project_config.repo_root,
            "--variable",
            "org:test",
            "--outputdir",
            outputdir,
            "--tagstatexclude",
            "cci_metric_elapsed_time",
            "--tagstatexclude",
            "cci_metric",
            "tests",
        ]
        mock_robot_run.assert_not_called()
        mock_subprocess_run.assert_called_once_with(expected_cmd)

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_ordering_arg_processes_gt_1(self, mock_subprocess_run, mock_robot_run):
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        task = create_task(
            Robot, {"suites": "tests", "processes": "2", "ordering": "robot/order.txt"}
        )
        task()
        outputdir = str(Path(".").resolve())
        expected_cmd = [
            sys.executable,
            "-m",
            "pabot.pabot",
            "--pabotlib",
            "--processes",
            "2",
            # note: we are specifically testing that this comes before --pythonpath
            "--ordering",
            "robot/order.txt",
            "--pythonpath",
            task.project_config.repo_root,
            "--variable",
            "org:test",
            "--outputdir",
            outputdir,
            "--tagstatexclude",
            "cci_metric_elapsed_time",
            "--tagstatexclude",
            "cci_metric",
            "tests",
        ]
        mock_robot_run.assert_not_called()
        mock_subprocess_run.assert_called_once_with(expected_cmd)

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_testlevelsplit_arg_processes_gt_1(
        self, mock_subprocess_run, mock_robot_run
    ):
        mock_subprocess_run.return_value = mock.Mock(returncode=0)
        task = create_task(
            Robot, {"suites": "tests", "processes": "2", "testlevelsplit": "true"}
        )
        task()
        outputdir = str(Path(".").resolve())
        expected_cmd = [
            sys.executable,
            "-m",
            "pabot.pabot",
            "--pabotlib",
            "--processes",
            "2",
            # note: we are specifically testing that this comes before --pythonpath
            # and that the option isn't followed by a value
            "--testlevelsplit",
            "--pythonpath",
            task.project_config.repo_root,
            "--variable",
            "org:test",
            "--outputdir",
            outputdir,
            "--tagstatexclude",
            "cci_metric_elapsed_time",
            "--tagstatexclude",
            "cci_metric",
            "tests",
        ]
        mock_robot_run.assert_not_called()
        mock_subprocess_run.assert_called_once_with(expected_cmd)

    @mock.patch("cumulusci.tasks.robotframework.robotframework.robot_run")
    @mock.patch("cumulusci.tasks.robotframework.robotframework.subprocess.run")
    def test_pabot_args_process_eq_zero(self, mock_subprocess_run, mock_robot_run):
        """Verifies that pabot-specific options are not passed on when processes=1"""
        mock_robot_run.return_value = 0
        task = create_task(
            Robot,
            {
                "suites": "tests",
                "processes": 1,
                "testlevelsplit": "true",
                "ordering": "./robot/order.txt",
            },
        )
        task()
        mock_subprocess_run.assert_not_called()
        outputdir = str(Path(".").resolve())
        mock_robot_run.assert_called_once_with(
            "tests",
            listener=[],
            outputdir=outputdir,
            variable=["org:test"],
            tagstatexclude=["cci_metric_elapsed_time", "cci_metric"],
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
