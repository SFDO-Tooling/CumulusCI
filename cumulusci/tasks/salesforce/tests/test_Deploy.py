import base64
import io
import os
import unittest
import zipfile

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.core.flowrunner import StepSpec
from cumulusci.tasks.salesforce import Deploy
from cumulusci.utils import cd
from cumulusci.utils import temporary_dir
from cumulusci.utils import touch
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
            task = create_task(Deploy, {"path": path, "clean_meta_xml": False})

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

    def test_include_directory(self):
        # create task
        task = create_task(
            Deploy,
            {
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )

        # include root directory
        self.assertEqual(True, task._include_directory([]))

        # not include lwc directory
        self.assertEqual(False, task._include_directory(["lwc"]))

        # include any lwc sub-directory (i.e. lwc component directory)
        self.assertEqual(True, task._include_directory(["lwc", "myComponent"]))
        self.assertEqual(True, task._include_directory(["lwc", "lwc"]))

        # not include any sub-*-directory of a lwc sub-directory
        self.assertEqual(
            False, task._include_directory(["lwc", "myComponent", "__tests__"])
        )
        self.assertEqual(
            False, task._include_directory(["lwc", "myComponent", "sub-1", "sub-2"])
        )
        self.assertEqual(
            False,
            task._include_directory(["lwc", "myComponent", "sub-1", "sub-2", "sub-3"]),
        )
        self.assertEqual(
            False,
            task._include_directory(
                ["lwc", "myComponent", "sub-1", "sub-2", "sub-3", "sub-4"]
            ),
        )

        # include any non-lwc directory
        self.assertEqual(True, task._include_directory(["not-lwc"]))
        self.assertEqual(True, task._include_directory(["classes"]))
        self.assertEqual(True, task._include_directory(["objects"]))

        # include any sub_* directory of a non-lwc directory
        self.assertEqual(True, task._include_directory(["not-lwc", "sub-1"]))
        self.assertEqual(True, task._include_directory(["not-lwc", "sub-1", "sub-2"]))
        self.assertEqual(
            True, task._include_directory(["not-lwc", "sub-1", "sub-2", "sub-3"])
        )
        self.assertEqual(
            True,
            task._include_directory(["not-lwc", "sub-1", "sub-2", "sub-3", "sub-4"]),
        )

    def test_include_file(self):
        # create task
        task = create_task(
            Deploy,
            {
                "path": "path",
                "namespace_tokenize": "ns",
                "namespace_inject": "ns",
                "namespace_strip": "ns",
            },
        )

        lwc_component_directory = ["lwc", "myComponent"]
        non_lwc_component_directories = [
            [],
            ["lwc"],
            ["lwc", "myComponent", "sub-1"],
            ["lwc", "myComponent", "sub-2"],
            ["classes"],
            ["objects", "sub-1"],
            ["objects", "sub-1", "sub-2"],
        ]

        # file endings in lwc component whitelist
        for file_ending in [".js", ".js-meta.xml", ".html", ".css", ".svg"]:
            # lwc_component_directory
            self.assertEqual(
                True,
                task._include_file(lwc_component_directory, "file_name" + file_ending),
            )

            # non_lwc_component_directories
            for d in non_lwc_component_directories:
                self.assertEqual(True, task._include_file(d, "file_name" + file_ending))

        # file endings not in lwc component whitelist
        for file_ending in ["", ".json", ".xml", ".cls", ".cls-meta.xml", ".object"]:
            # lwc_component_directory
            self.assertEqual(
                False,
                task._include_file(lwc_component_directory, "file_name" + file_ending),
            )

            # non_lwc_component_directories
            for d in non_lwc_component_directories:
                self.assertEqual(True, task._include_file(d, "file_name" + file_ending))

    def test_get_files_to_package(self):
        with temporary_dir() as path:
            expected = []

            rel_path = "."

            # add package.xml
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>45.0</version>
</Package>"""
                )
                expected.append(os.path.join(rel_path, "package.xml"))

            # add lwc
            lwc_path = os.path.join(path, "lwc")
            rel_lwc_path = os.path.join(rel_path, "lwc")
            os.mkdir(lwc_path)

            # add lwc linting files (not included in zip)
            lwc_ignored_files = [".eslintrc.json", "jsconfig.json"]
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_path, lwc_ignored_file))

            # add lwc component
            lwc_component_path = os.path.join(lwc_path, "myComponent")
            rel_lwc_component_path = os.path.join(rel_lwc_path, "myComponent")
            os.mkdir(lwc_component_path)

            # add lwc component files included in zip (in alphabetical order)
            lwc_component_files = [
                {"name": "myComponent.html"},
                {"name": "myComponent.js"},
                {
                    "name": "myComponent.js-meta.xml",
                    "body:": """<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata" fqn="myComponent">
    <apiVersion>45.0</apiVersion>
    <isExposed>false</isExposed>
</LightningComponentBundle>""",
                },
                {"name": "myComponent.svg"},
                {"name": "myComponent.css"},
            ]
            for lwc_component_file in lwc_component_files:
                with open(
                    os.path.join(lwc_component_path, lwc_component_file.get("name")),
                    "w",
                ) as f:
                    if lwc_component_file.get("body") is not None:
                        f.write(lwc_component_file.get("body"))
                    expected.append(
                        os.path.join(
                            rel_lwc_component_path, lwc_component_file.get("name")
                        )
                    )

            # add lwc component files not included in zip
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_component_path, lwc_ignored_file))

            # add lwc component sub-directory and files not included in zip
            lwc_component_test_path = os.path.join(lwc_component_path, "__tests__")
            os.mkdir(lwc_component_test_path)
            touch(os.path.join(lwc_component_test_path, "test.js"))

            # add classes
            classes_path = os.path.join(path, "classes")
            rel_classes_path = os.path.join(rel_path, "classes")
            os.mkdir(classes_path)
            class_files = [
                {
                    "name": "MyClass.cls-meta.xml",
                    "body": """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>45.0</apiVersion>
    <status>Active</status>
</ApexClass>
""",
                },
                {"name": "MyClass.cls"},
            ]
            for class_file in class_files:
                with open(os.path.join(classes_path, class_file.get("name")), "w") as f:
                    if class_file.get("body") is not None:
                        f.write(class_file.get("body"))
                    expected.append(
                        os.path.join(rel_classes_path, class_file.get("name"))
                    )

            # add objects
            objects_path = os.path.join(path, "objects")
            rel_objects_path = os.path.join(rel_path, "objects")
            os.mkdir(objects_path)
            object_file_names = ["Account.object", "Contact.object", "CustomObject__c"]
            object_file_names.sort()
            for object_file_name in object_file_names:
                with open(os.path.join(objects_path, object_file_name), "w"):
                    expected.append(os.path.join(rel_objects_path, object_file_name))

            # add sub-directory of objects (that doesn't really exist)
            objects_sub_path = os.path.join(objects_path, "does-not-exist-in-schema")
            rel_objects_sub_path = os.path.join(
                rel_objects_path, "does-not-exist-in-schema"
            )
            os.mkdir(objects_sub_path)
            with open(os.path.join(objects_sub_path, "some.file"), "w"):
                expected.append(os.path.join(rel_objects_sub_path, "some.file"))

            # test
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                },
            )

            expected_set = set(expected)
            actual_set = set(task._get_files_to_package())
            self.assertEqual(expected_set, actual_set)

    def test_get_package_zip(self):
        with temporary_dir() as path:

            # add package.xml
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>45.0</version>
</Package>"""
                )

            # add lwc
            lwc_path = os.path.join(path, "lwc")
            os.mkdir(lwc_path)

            # add lwc linting files (not included in zip)
            lwc_ignored_files = [".eslintrc.json", "jsconfig.json"]
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_path, lwc_ignored_file))

            # add lwc component
            lwc_component_path = os.path.join(lwc_path, "myComponent")
            os.mkdir(lwc_component_path)

            # add lwc component files included in zip (in alphabetical order)
            lwc_component_files = [
                {"name": "myComponent.html"},
                {"name": "myComponent.js"},
                {
                    "name": "myComponent.js-meta.xml",
                    "body:": """<?xml version="1.0" encoding="UTF-8"?>
<LightningComponentBundle xmlns="http://soap.sforce.com/2006/04/metadata" fqn="myComponent">
    <apiVersion>45.0</apiVersion>
    <isExposed>false</isExposed>
</LightningComponentBundle>""",
                },
                {"name": "myComponent.svg"},
                {"name": "myComponent.css"},
            ]
            for lwc_component_file in lwc_component_files:
                with open(
                    os.path.join(lwc_component_path, lwc_component_file.get("name")),
                    "w",
                ) as f:
                    if lwc_component_file.get("body") is not None:
                        f.write(lwc_component_file.get("body"))

            # add lwc component files not included in zip
            for lwc_ignored_file in lwc_ignored_files:
                touch(os.path.join(lwc_component_path, lwc_ignored_file))

            # add lwc component sub-directory and files not included in zip
            lwc_component_test_path = os.path.join(lwc_component_path, "__tests__")
            os.mkdir(lwc_component_test_path)
            touch(os.path.join(lwc_component_test_path, "test.js"))

            # add classes
            classes_path = os.path.join(path, "classes")
            os.mkdir(classes_path)
            class_files = [
                {
                    "name": "MyClass.cls-meta.xml",
                    "body": """<?xml version="1.0" encoding="UTF-8"?>
<ApexClass xmlns="http://soap.sforce.com/2006/04/metadata">
    <apiVersion>45.0</apiVersion>
    <status>Active</status>
</ApexClass>
""",
                },
                {"name": "MyClass.cls"},
            ]
            for class_file in class_files:
                with open(os.path.join(classes_path, class_file.get("name")), "w") as f:
                    if class_file.get("body") is not None:
                        f.write(class_file.get("body"))

            # add objects
            objects_path = os.path.join(path, "objects")
            os.mkdir(objects_path)
            object_file_names = ["Account.object", "Contact.object", "CustomObject__c"]
            object_file_names.sort()
            for object_file_name in object_file_names:
                touch(os.path.join(objects_path, object_file_name))

            # add sub-directory of objects (that doesn't really exist)
            objects_sub_path = os.path.join(objects_path, "does-not-exist-in-schema")
            os.mkdir(objects_sub_path)
            touch(os.path.join(objects_sub_path, "some.file"))

            # test
            task = create_task(
                Deploy,
                {
                    "path": path,
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                },
            )

            zip_bytes = io.BytesIO()
            zipf = zipfile.ZipFile(zip_bytes, "w", zipfile.ZIP_DEFLATED)

            with cd(path):
                for file_to_package in task._get_files_to_package():
                    zipf.write(file_to_package)
                zipf.close()

            zipf_processed = task._process_zip_file(zipfile.ZipFile(zip_bytes))
            fp = zipf_processed.fp
            zipf_processed.close()
            expected = base64.b64encode(fp.getvalue()).decode("utf-8")

            actual = task._get_package_zip(path)

            self.assertEqual(expected, actual)

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
