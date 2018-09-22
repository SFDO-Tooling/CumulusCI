import mock
import os
import unittest

from cumulusci.tasks.salesforce import RetrieveUnpackaged
from cumulusci.utils import temporary_dir
from .util import create_task


class TestRetrieveUnpackaged(unittest.TestCase):
    def test_get_api(self):
        with temporary_dir() as path:
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write("PACKAGE")
            task = create_task(
                RetrieveUnpackaged,
                {"path": path, "package_xml": "package.xml", "api_version": "43.0"},
            )
            task.api_class = mock.Mock()
            task._get_api()
            self.assertEqual("PACKAGE", task.api_class.call_args[0][1])
