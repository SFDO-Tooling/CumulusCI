import mock
import os

from cumulusci.tasks.salesforce import DeployBundles
from cumulusci.utils import temporary_dir
from .util import SalesforceTaskTestCase


class TestDeployBundles(SalesforceTaskTestCase):
    task_class = DeployBundles

    def test_run_task(self):
        with temporary_dir() as path:
            os.mkdir("src")
            with open(os.path.join(path, "file"), "w"):
                pass
            task = self.create_task({"path": path})
            task._get_api = mock.Mock()
            task()
            task._get_api.assert_called_once()

    def test_run_task__path_not_found(self):
        with temporary_dir() as path:
            pass
        task = self.create_task({"path": path})
        task._get_api = mock.Mock()
        task()
        task._get_api.assert_not_called()
