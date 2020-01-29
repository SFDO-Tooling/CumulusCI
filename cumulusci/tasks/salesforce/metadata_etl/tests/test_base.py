from pathlib import Path
import tempfile
import unittest
from unittest import mock

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce.tests.util import create_task
from cumulusci.tasks.salesforce.metadata_etl import (
    BaseMetadataETLTask,
    BaseMetadataSynthesisTask,
    BaseMetadataTransformTask,
    MetadataSingleEntityTransformTask,
)


class test_BaseMetadataETLTask(unittest.TestCase):
    def test_init_options(self):
        task = create_task(
            BaseMetadataETLTask, {"unmanaged": True, "api_version": "47.0"}
        )

        assert task.options["unmanaged"]
        assert task.options["api_version"] == "47.0"

    def test_namespace_injector(self):
        task = create_task(
            BaseMetadataETLTask,
            {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
        )

        ns = task._namespace_injector

        assert ns("%%%NAMESPACE%%%Test__c") == "test__Test__c"
        task.options["unmanaged"] = True
        assert ns("%%%NAMESPACE%%%Test__c") == "Test__c"

    def test_generate_package_xml(self):
        task = create_task(
            BaseMetadataETLTask,
            {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
        )

        assert "47.0" in task._generate_package_xml()

    @mock.patch("cumulusci.tasks.salesforce.metadata_etl.base.ApiRetrieveUnpackaged")
    def test_retrieve(self, api_mock):
        task = create_task(
            BaseMetadataETLTask,
            {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
        )
        task.retrieve_dir = mock.Mock()

        task._retrieve()
        api_mock.assert_called_once_with(task, task._generate_package_xml(), "47.0")
        api_mock.return_value.assert_called_once_with()
        api_mock.return_value.return_value.extractall.assert_called_once_with(
            task.retrieve_dir
        )

    @mock.patch("cumulusci.tasks.salesforce.metadata_etl.base.Deploy")
    @mock.patch("cumulusci.tasks.salesforce.metadata_etl.base.PackageXmlGenerator")
    def test_deploy(self, package_mock, deploy_mock):
        with tempfile.TemporaryDirectory() as tmpdir:
            task = create_task(
                BaseMetadataETLTask,
                {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
            )
            task.deploy_dir = Path(tmpdir)

            package_mock.return_value.return_value = "test"
            result = task._deploy()

            package_mock.assert_called_once_with(str(Path(tmpdir)), "47.0")
            assert (Path(tmpdir) / "package.xml").read_text() == "test"

            assert len(deploy_mock.call_args_list) == 1

            assert deploy_mock.call_args_list[0][0][0] == task.project_config
            assert deploy_mock.call_args_list[0][0][2] == task.org_config
            deploy_mock.return_value.assert_called_once_with()
            assert result == deploy_mock.return_value.return_value


class test_BaseMetadataSynthesisTask(unittest.TestCase):
    def test_synthesis(self):
        task = create_task(
            BaseMetadataSynthesisTask,
            {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
        )

        task._deploy = mock.Mock()
        task._synthesize = mock.Mock()

        task()

        task._deploy.assert_called_once_with()
        task._synthesize.assert_called_once_with()


class test_BaseMetadataTransformTask(unittest.TestCase):
    def test_generate_package_xml(self):
        task = create_task(
            BaseMetadataTransformTask,
            {"unmanaged": False, "namespace_inject": "test", "api_version": "47.0"},
        )
        assert task._get_entities() == {}

        task._get_entities = mock.Mock()
        task._get_entities.return_value = {
            "CustomObject": ["Account", "Contact"],
            "ApexClass": ["Test"],
        }

        assert (
            task._generate_package_xml()
            == """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Account</members>
        <members>Contact</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>Test</members>
        <name>ApexClass</name>
    </types>

    <version>47.0</version>
</Package>
"""
        )


class test_MetadataSingleEntityTransformTask(unittest.TestCase):
    def test_init_options(self):
        task = create_task(MetadataSingleEntityTransformTask, {})
        task._init_options(
            {
                "unmanaged": False,
                "api_version": "47.0",
                "namespace_inject": "test",
                "api_names": "%%%NAMESPACE%%%bar,foo",
            }
        )
        assert task.api_names == ["test__bar", "foo"]

    def test_get_entities(self):
        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0", "api_names": "bar,foo"},
        )

        assert task._get_entities() == {None: ["bar", "foo"]}

        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0"},
        )

        assert task._get_entities() == {None: ["*"]}

    def test_transform_entity(self):
        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0", "api_names": "bar,foo"},
        )

        assert task._transform_entity("test", "test.cls") == "test"

    def test_transform(self):
        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0", "api_names": "Test"},
        )

        task.entity = "CustomApplication"

        with tempfile.TemporaryDirectory() as tmpdir:
            task._create_directories(tmpdir)

            test_path = task.retrieve_dir / "applications"
            test_path.mkdir()
            test_path = test_path / "Test.app"

            test_path.write_text(
                """<?xml version="1.0" encoding="UTF-8"?>
<CustomApplication xmlns="http://soap.sforce.com/2006/04/metadata">
</CustomApplication>"""
            )

            task._transform()

            assert (task.deploy_dir / "applications" / "Test.app").exists()

    def test_transform__bad_entity(self):
        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0", "api_names": "bar,foo"},
        )

        task.entity = "Battlestar"

        with self.assertRaises(CumulusCIException):
            task._transform()

    def test_transform__non_xml_entity(self):
        task = create_task(
            MetadataSingleEntityTransformTask,
            {"unmanaged": False, "api_version": "47.0", "api_names": "bar,foo"},
        )

        task.entity = "LightningComponentBundle"

        with self.assertRaises(CumulusCIException):
            task._transform()
