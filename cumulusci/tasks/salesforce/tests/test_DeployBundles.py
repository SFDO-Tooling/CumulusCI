import mock
import os
import unittest

from cumulusci.tasks.salesforce import DeployBundles
from cumulusci.utils import temporary_dir
from .util import create_task


class TestDeployBundles(unittest.TestCase):
    def test_run_task(self):
        with temporary_dir() as path:
            os.mkdir("src")
            with open(os.path.join(path, "file"), "w"):
                pass
            task = create_task(DeployBundles, {"path": path})
            task._get_api = mock.Mock()
            task()
            task._get_api.assert_called_once()

    def test_run_task__path_not_found(self):
        with temporary_dir() as path:
            pass
        task = create_task(DeployBundles, {"path": path})
        task._get_api = mock.Mock()
        task()
        task._get_api.assert_not_called()
