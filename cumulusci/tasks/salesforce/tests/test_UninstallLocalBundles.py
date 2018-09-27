import mock
import os
import unittest

from cumulusci.tasks.salesforce import UninstallLocalBundles
from cumulusci.utils import temporary_dir
from .util import create_task


class TestUninstallLocalBundles(unittest.TestCase):
    def test_run_task(self):
        with temporary_dir() as path:
            os.mkdir("bundle")
            with open(os.path.join(path, "file"), "w"):
                pass
            task = create_task(UninstallLocalBundles, {"path": path})
            task._get_api = mock.Mock()
            task()
            task._get_api.assert_called_once()
