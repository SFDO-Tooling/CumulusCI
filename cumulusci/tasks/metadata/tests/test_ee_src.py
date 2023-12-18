import os
import time
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
    def test_run_task(self, tmp_path):
        revert_path = tmp_path / "revert"
        revert_path.mkdir()
        file_path = revert_path / "file"
        file_path.write_text("content")

        path = tmp_path / "path"
        path.mkdir()
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig(
            {"options": {"path": str(path), "revert_path": str(revert_path)}}
        )
        task = RevertUnmanagedEESrc(project_config, task_config)
        task()
        assert (path / "file").exists()

    def test_run_task__revert_path_not_found(self):
        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig({"options": {"path": "bogus", "revert_path": "bogus"}})
        task = RevertUnmanagedEESrc(project_config, task_config)
        with pytest.raises(TaskOptionsError):
            task()

    def test_revert_with_update(self, tmp_path):
        """
        Test the 'update' behavior of RevertUnmanagedEESrc task with temporary directories.

        This test creates a source and a destination directory each with one
        file. The file in the source directory has an older timestamp. After
        running RevertUnmanagedEESrc, it checks that the destination file is not
        overwritten by the older source file, confirming the update logic.
        """
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        source_file = source_dir / "testfile.txt"
        source_file.write_text("original content")

        dest_dir = tmp_path / "dest"
        dest_dir.mkdir()
        dest_file = dest_dir / "testfile.txt"
        dest_file.write_text("modified content")

        # Ensure the source file has an older timestamp
        past_time = time.time() - 100
        # Use os.utime to modify the timestamp
        source_file.touch()
        os.utime(str(source_file), (past_time, past_time))

        project_config = BaseProjectConfig(UniversalConfig(), config={"noyaml": True})
        task_config = TaskConfig(
            {"options": {"path": str(dest_dir), "revert_path": str(source_dir)}}
        )
        task = RevertUnmanagedEESrc(project_config, task_config)
        task()

        # Verify that the destination file was not updated (due to older source file)
        assert dest_file.read_text() == "modified content"
