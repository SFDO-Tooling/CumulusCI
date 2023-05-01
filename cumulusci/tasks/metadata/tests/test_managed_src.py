import os

import pytest

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata.managed_src import CreateManagedSrc, RevertManagedSrc
from cumulusci.utils import temporary_dir


class TestCreateManagedSrc:
    def test_run_task(self):
        with temporary_dir() as path:
            os.mkdir(os.path.join(path, "classes"))
            class_path = os.path.join(path, "classes", "test.cls")
            with open(class_path, "w") as f:
                f.write("//cumulusci-managed")
            revert_path = os.path.join(
                os.path.dirname(path), os.path.basename(path) + "_revert"
            )
            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig(
                {"options": {"path": path, "revert_path": revert_path}}
            )
            task = CreateManagedSrc(project_config, task_config)
            task()
            with open(class_path, "r") as f:
                result = f.read()
            assert result == ""

    def test_run_task__path_not_found(self):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": {"path": "bogus", "revert_path": "bogus"}})
        task = CreateManagedSrc(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task()

    def test_run_task__revert_path_already_exists(self):
        with temporary_dir() as path, temporary_dir() as revert_path:
            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig(
                {"options": {"path": path, "revert_path": revert_path}}
            )
            task = CreateManagedSrc(project_config, task_config)
            with pytest.raises(TaskOptionsError):
                task()


class TestRevertManagedSrc:
    def test_run_task(self):
        with temporary_dir() as revert_path:
            with open(os.path.join(revert_path, "file"), "w"):
                pass
            path = os.path.join(
                os.path.dirname(revert_path), os.path.basename(revert_path) + "_orig"
            )
            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig(
                {"options": {"path": path, "revert_path": revert_path}}
            )
            task = RevertManagedSrc(project_config, task_config)
            task()
            assert os.path.exists(os.path.join(path, "file"))

    def test_run_task__revert_path_not_found(self):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": {"path": "bogus", "revert_path": "bogus"}})
        task = RevertManagedSrc(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task()
