from pathlib import Path
from unittest import mock
import unittest
from cumulusci.robotframework.CumulusCI import CumulusCI
from cumulusci.core.config import UniversalConfig, BaseProjectConfig
from cumulusci.core.tests.utils import MockLoggerMixin
from cumulusci.core.exceptions import TaskNotFoundError
from cumulusci.utils import temporary_dir


class TestCumulusCILibrary(MockLoggerMixin, unittest.TestCase):
    def setUp(self):
        self.universal_config = UniversalConfig()
        self.project_config = BaseProjectConfig(
            self.universal_config,
            {
                "project": {"name": "Test"},
                "tasks": {
                    "get_pwd": {
                        "class_path": "cumulusci.tasks.command.Command",
                        "options": {
                            "command": "pwd",
                        },
                    },
                },
                "sources": {
                    "example": {"path": "/tmp"},
                },
            },
        )
        self.cumulusci = CumulusCI()
        self.cumulusci._project_config = self.project_config
        self.cumulusci._org = mock.Mock()

        self._task_log_handler.reset()
        self.task_log = self._task_log_handler.messages

    def test_run_task(self):
        """Smoke test; can we run the command task?"""
        self.cumulusci.run_task("get_pwd")
        self.assertIn("Running command: pwd", self.task_log["info"])

    def test_run_unknown_task(self):
        with self.assertRaises(TaskNotFoundError):
            self.cumulusci.run_task("bogus")

    def test_cross_project_task(self):
        """Verify that the cross-project task runs with the project config of the task
        See W-8891667
        """
        with temporary_dir() as tmpdir:
            tmpdir = Path(tmpdir).resolve()
            cumulusci_yml_path = tmpdir / "cumulusci.yml"
            with open(cumulusci_yml_path, "w+") as cumulusci_yml:
                self.project_config.sources["example"] = {"path": tmpdir}
                cumulusci_yml.write(
                    """
                    tasks:
                        whatever:
                            class_path: cumulusci.tasks.command.Command
                            options:
                                command: pwd
                    """
                )

            with mock.patch.object(self.cumulusci, "_run_task"):
                self.cumulusci.run_task("example:whatever")
                task = self.cumulusci._run_task.mock_calls[0].args[0]

                # make sure it's not using the current project config
                # for the task, and that the config it _is_ using is
                # rooted in the directory we created
                self.assertNotEqual(task.project_config, self.cumulusci.project_config)
                self.assertEqual(tmpdir, Path(task.project_config.repo_root))
                print("bruh")
