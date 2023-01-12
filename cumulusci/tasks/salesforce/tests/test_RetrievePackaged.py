import io
import os
import zipfile
from unittest import mock

from cumulusci.tasks.salesforce import RetrievePackaged
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir

from .util import create_task


class TestRetrievePackaged:
    def test_run_task(self):
        with temporary_dir() as path:
            project_config = create_project_config()
            project_config.config["project"]["package"]["name"] = "TestPackage"
            task = create_task(RetrievePackaged, {"path": path}, project_config)
            zf = zipfile.ZipFile(io.BytesIO(), "w")
            zf.writestr("TestPackage/testfile", "test")
            task.api_class = mock.Mock(return_value=mock.Mock(return_value=zf))
            task()
            assert os.path.exists(os.path.join(path, "testfile"))
