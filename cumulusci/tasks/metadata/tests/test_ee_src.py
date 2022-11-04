import os
from unittest import mock

import pytest

from cumulusci.core.config import BaseProjectConfig, TaskConfig, UniversalConfig
from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.metadata.ee_src import CreateUnmanagedEESrc, RevertUnmanagedEESrc
from cumulusci.utils import temporary_dir


class TestCreateUnmanagedEESrc:
    @mock.patch("cumulusci.tasks.metadata.ee_src.remove_xml_element_directory")
    def test_run_task(self, remove_xml_element_directory):
        with temporary_dir() as path:
            revert_path = os.path.join(
                os.path.dirname(path), os.path.basename(path) + "_revert"
            )
            project_config = BaseProjectConfig(
                UniversalConfig(), config={"noyaml": True}
            )
            task_config = TaskConfig(
                {"options": {"path": path, "revert_path": revert_path}}
            )
            task = CreateUnmanagedEESrc(project_config, task_config)
            task()
            remove_xml_element_directory.assert_has_calls(
                [
                    mock.call("availableFields", path, "*.object"),
                    mock.call("visibility[.='Protected']", path, "*.object"),
                ]
            )

    def test_run_task__path_not_found(self):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": {"path": "bogus", "revert_path": "bogus"}})
        task = CreateUnmanagedEESrc(project_config, task_config)
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
            task = CreateUnmanagedEESrc(project_config, task_config)
            with pytest.raises(TaskOptionsError):
                task()


class TestRevertUnmanagedEESrc:
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
            task = RevertUnmanagedEESrc(project_config, task_config)
            task()
            assert os.path.exists(os.path.join(path, "file"))

    def test_run_task__revert_path_not_found(self):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": {"path": "bogus", "revert_path": "bogus"}})
        task = RevertUnmanagedEESrc(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task()
