import base64
import io
import os
import pathlib
import zipfile

import pytest

from cumulusci.salesforce_api.package_zip import (
    BasePackageZipBuilder,
    CreatePackageZipBuilder,
    DestructiveChangesZipBuilder,
    InstallPackageZipBuilder,
    MetadataPackageZipBuilder,
    UninstallPackageZipBuilder,
)
from cumulusci.utils import temporary_dir, touch


class TestBasePackageZipBuilder:
    def test_as_hash(self):
        builder = BasePackageZipBuilder()
        builder.zf.writestr("1", "1")
        hash1 = builder.as_hash()

        builder = BasePackageZipBuilder()
        builder.zf.writestr("1", "1")
        hash2 = builder.as_hash()

        assert hash2 == hash1

        builder.zf.writestr("2", "2")
        hash3 = builder.as_hash()
        assert hash3 != hash2


class TestMetadataPackageZipBuilder:
    def test_builder(self, task_context):
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
            builder = MetadataPackageZipBuilder(
                path=path,
                options={
                    "namespace_tokenize": "ns",
                    "namespace_inject": "ns",
                    "namespace_strip": "ns",
                },
                context=task_context,
            )

            # make sure result can be read as a zipfile
            result = builder.as_base64()
            zf = zipfile.ZipFile(io.BytesIO(base64.b64decode(result)), "r")
            assert set(zf.namelist()) == {
                "package.xml",
                "lwc/myComponent/myComponent.html",
                "lwc/myComponent/myComponent.js",
                "lwc/myComponent/myComponent.js-meta.xml",
                "lwc/myComponent/myComponent.svg",
                "lwc/myComponent/myComponent.css",
                "classes/MyClass.cls-meta.xml",
                "classes/MyClass.cls",
                "objects/Account.object",
                "objects/Contact.object",
                "objects/CustomObject__c",
                "objects/does-not-exist-in-schema/some.file",
            }
            zf.close()

    def test_add_files_to_package(self, task_context):
        with temporary_dir() as path:
            expected = []

            # add package.xml
            with open(os.path.join(path, "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <version>45.0</version>
</Package>"""
                )
                expected.append("package.xml")

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
                    expected.append(f"lwc/myComponent/{lwc_component_file.get('name')}")

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
                    expected.append(f"classes/{class_file.get('name')}")

            # add objects
            objects_path = os.path.join(path, "objects")
            os.mkdir(objects_path)
            object_file_names = ["Account.object", "Contact.object", "CustomObject__c"]
            object_file_names.sort()
            for object_file_name in object_file_names:
                with open(os.path.join(objects_path, object_file_name), "w"):
                    expected.append(f"objects/{object_file_name}")

            # add sub-directory of objects (that doesn't really exist)
            objects_sub_path = os.path.join(objects_path, "does-not-exist-in-schema")
            os.mkdir(objects_sub_path)
            with open(os.path.join(objects_sub_path, "some.file"), "w"):
                expected.append("objects/does-not-exist-in-schema/some.file")

            # test
            builder = MetadataPackageZipBuilder(context=task_context)

            expected_set = set(expected)
            builder._add_files_to_package(path)
            actual_set = set(builder.zf.namelist())
            assert expected_set == actual_set

    def test_include_directory(self, task_context):
        builder = MetadataPackageZipBuilder(context=task_context)

        # include root directory
        assert builder._include_directory([]) is True

        # not include lwc directory
        assert builder._include_directory(["lwc"]) is True

        # include any lwc sub-directory (i.e. lwc component directory)
        assert builder._include_directory(["lwc", "myComponent"]) is True
        assert builder._include_directory(["lwc", "lwc"]) is True
        assert (
            builder._include_directory(["lwc", "myComponent", "sub-1", "sub-2"]) is True
        )

        # don't include __tests__ within lwc components
        assert not builder._include_directory(["lwc", "myComponent", "__tests__"])
        assert not builder._include_directory(["lwc", "myComponent", "__mocks__"])

        # include any non-lwc directory
        assert builder._include_directory(["not-lwc"]) is True
        assert builder._include_directory(["classes"]) is True
        assert builder._include_directory(["objects"]) is True

        # include any sub_* directory of a non-lwc directory
        assert builder._include_directory(["not-lwc", "sub-1"]) is True
        assert builder._include_directory(["not-lwc", "sub-1", "sub-2"]) is True

    def test_include_file(self, task_context):
        builder = MetadataPackageZipBuilder(context=task_context)

        lwc_component_directories = [
            ["lwc"],
            ["lwc", "myComponent"],
            ["lwc", "myComponent", "sub-1"],
            ["lwc", "myComponent", "sub-2"],
        ]
        non_lwc_component_directories = [
            [],
            ["classes"],
            ["objects", "sub-1"],
            ["objects", "sub-1", "sub-2"],
        ]

        # file endings in lwc component whitelist
        for file_ending in [".js", ".js-meta.xml", ".html", ".css", ".svg"]:
            for d in lwc_component_directories:
                assert builder._include_file(d, "file_name" + file_ending)
            for d in non_lwc_component_directories:
                assert builder._include_file(d, "file_name" + file_ending)

        # file endings not in lwc component whitelist
        for file_ending in ["", ".json", ".xml", ".cls", ".cls-meta.xml", ".object"]:
            for d in lwc_component_directories:
                assert not builder._include_file(d, "file_name" + file_ending)
            for d in non_lwc_component_directories:
                assert builder._include_file(d, "file_name" + file_ending)

    def test_removes_feature_parameters_from_unlocked_package(self, task_context):
        with temporary_dir() as path:
            pathlib.Path(path, "package.xml").write_text(
                """<?xml version="1.0" encoding="utf-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <name>FeatureParameterInteger</name>
    </types>
</Package>"""
            )
            featureParameters = pathlib.Path(path, "featureParameters")
            featureParameters.mkdir()
            (featureParameters / "test.featureParameterInteger").touch()
            builder = MetadataPackageZipBuilder(
                path=path, options={"package_type": "Unlocked"}, context=task_context
            )
            assert (
                "featureParameters/test.featureParameterInteger"
                not in builder.zf.namelist()
            )
            package_xml = builder.zf.read("package.xml")
            assert b"FeatureParameterInteger" not in package_xml


class TestCreatePackageZipBuilder:
    def test_init__missing_name(self):
        with pytest.raises(ValueError):
            CreatePackageZipBuilder(None, "43.0")

    def test_init__missing_api_version(self):
        with pytest.raises(ValueError):
            CreatePackageZipBuilder("TestPackage", None)


class TestInstallPackageZipBuilder:
    def test_init__missing_namespace(self):
        with pytest.raises(ValueError):
            InstallPackageZipBuilder(None, "1.0")

    def test_init__missing_version(self):
        with pytest.raises(ValueError):
            InstallPackageZipBuilder("testns", None)


class TestDestructiveChangesZipBuilder:
    def test_call(self):
        builder = DestructiveChangesZipBuilder("", "1.0")
        names = builder.zf.namelist()
        assert "package.xml" in names
        assert "destructiveChanges.xml" in names


class TestUninstallPackageZipBuilder:
    def test_init__missing_namespace(self):
        with pytest.raises(ValueError):
            UninstallPackageZipBuilder(None, "1.0")

    def test_call(self):
        builder = UninstallPackageZipBuilder("testns", "1.0")
        assert "destructiveChanges.xml" in builder.zf.namelist()
