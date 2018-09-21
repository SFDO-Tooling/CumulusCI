import base64
import io
import mock
import os
import zipfile

from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import temporary_dir
from .util import SalesforceTaskTestCase


class TestDeploy(SalesforceTaskTestCase):
    task_class = Deploy

    def test_get_api(self):
        with temporary_dir() as path:
            with open(os.path.join(path, "package.xml"), "w") as f:
                pass
            task = self.create_task(
                {
                    "path": path,
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                }
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())

    def test_get_api__managed(self):
        with temporary_dir() as path:
            with open(os.path.join(path, "package.xml"), "w") as f:
                pass
            task = self.create_task(
                {"path": path, "namespace_inject": "ns", "unmanaged": False}
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())

    def test_get_api__skip_clean_meta_xml(self):
        with temporary_dir() as path:
            with open(os.path.join(path, "package.xml"), "w") as f:
                pass
            task = self.create_task({"path": path, "clean_meta_xml": False})

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())
