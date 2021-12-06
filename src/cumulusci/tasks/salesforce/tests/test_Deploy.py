import base64
import io
import os
import unittest
import zipfile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import temporary_dir, touch

from .util import create_task


class TestDeploy(unittest.TestCase):
    def test_get_api(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())

    def test_get_api__managed(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy, {"path": path, "namespace_inject": "ns", "unmanaged": False}
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())

    def test_get_api__additional_options(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "test_level": "RunSpecifiedTests",
                    "specified_tests": "TestA,TestB",
                    "unmanaged": False,
                },
            )

            api = task._get_api()
            assert api.run_tests == ["TestA", "TestB"]
            assert api.test_level == "RunSpecifiedTests"

    def test_get_api__skip_clean_meta_xml(self):
        with temporary_dir() as path:
            touch("package.xml")
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "clean_meta_xml": False,
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
            self.assertIn("package.xml", zf.namelist())

    def test_get_api__static_resources(self):
        with temporary_dir() as path:
            with open("package.xml", "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <name>OtherType</name>
    </types>
</Package>"""
                )
                touch("otherfile")

            with temporary_dir() as static_resource_path:
                os.mkdir("TestBundle")
                touch("TestBundle/test.txt")
                touch("TestBundle.resource-meta.xml")

                task = create_task(
                    Deploy,
                    {
                        "path": path,
                        "static_resource_path": static_resource_path,
                        "namespace_tokenize": "ns",
                        "namespace_inject": "ns",
                        "namespace_strip": "ns",
                        "unmanaged": True,
                    },
                )

                api = task._get_api()
                zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(api.package_zip)), "r")
                namelist = zf.namelist()
                self.assertIn("staticresources/TestBundle.resource", namelist)
                self.assertIn("staticresources/TestBundle.resource-meta.xml", namelist)
                package_xml = zf.read("package.xml").decode()
                self.assertIn("<name>StaticResource</name>", package_xml)
                self.assertIn("<members>TestBundle</members>", package_xml)

    def test_get_api__missing_path(self):
        task = create_task(
            Deploy,
            {
                "path": "BOGUS",
                "unmanaged": True,
            },
        )

        api = task._get_api()
        assert api is None

    def test_get_api__empty_package_zip(self):
        with temporary_dir() as path:
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "unmanaged": True,
                },
            )

            api = task._get_api()
            assert api is None

    def test_init_options(self):
        with self.assertRaises(TaskOptionsError):
            create_task(
                Deploy,
                {
                    "path": "empty",
                    "test_level": "RunSpecifiedTests",
                    "unmanaged": False,
                },
            )

        with self.assertRaises(TaskOptionsError):
            create_task(
                Deploy, {"path": "empty", "test_level": "Test", "unmanaged": False}
            )

        with self.assertRaises(TaskOptionsError):
            create_task(
                Deploy,
                {
                    "path": "empty",
                    "test_level": "RunLocalTests",
                    "specified_tests": ["TestA"],
                    "unmanaged": False,
                },
            )

    def test_freeze_sets_kind(self):
        task = create_task(
            Deploy,
            {
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )
        step = StepSpec(
            step_num=1,
            task_name="deploy",
            task_config=task.task_config,
            task_class=None,
            project_config=task.project_config,
        )

        assert all(s["kind"] == "metadata" for s in task.freeze(step))
