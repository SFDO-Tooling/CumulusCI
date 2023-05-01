import io
import os
import zipfile
from unittest import mock

import pytest

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.salesforce import UninstallPackagedIncremental
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir

from .util import create_task


class TestUninstallPackagedIncremental:
    def test_get_destructive_changes(self):
        with temporary_dir():
            os.mkdir("src")
            with open(os.path.join("src", "package.xml"), "w") as f:
                f.write(
                    """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Class1</members>
        <members>Class2</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>Page1</members>
        <name>ApexPage</name>
    </types>
    <types>
        <name>Empty</name>
    </types>
    <version>43.0</version>
</Package>"""
                )
            project_config = create_project_config()
            project_config.config["project"]["package"]["name"] = "TestPackage"
            project_config.config["project"]["package"]["api_version"] = "43.0"
            task = create_task(
                UninstallPackagedIncremental,
                {
                    "ignore": {"ApexClass": ["Ignored"]},
                },
                project_config,
            )
            zf = zipfile.ZipFile(io.BytesIO(), "w")
            zf.writestr(
                "package.xml",
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
    <types>
        <members>Class1</members>
        <members>Class2</members>
        <members>Class3</members>
        <members>Ignored</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>Page1</members>
        <name>ApexPage</name>
    </types>
    <types>
        <members>Test__c-en_US</members>
        <members>Test__c-es_MX</members>
        <name>CustomObjectTranslation</name>
    </types>
    <types>
        <name>Empty</name>
    </types>
    <version>43.0</version>
</Package>""",
            )
            task._retrieve_packaged = mock.Mock(return_value=zf)
            result = task._get_destructive_changes()
            assert (
                """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Class3</members>
        <name>ApexClass</name>
    </types>
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
    <version>43.0</version>
</Package>"""
                == result
            )
            zf.close()

    def test_get_destructive_changes__no_package_xml(self):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        project_config.config["project"]["package"]["api_version"] = "43.0"
        task = create_task(
            UninstallPackagedIncremental,
            {
                "ignore": {"ApexClass": ["Ignored"]},
            },
            project_config,
        )
        with pytest.raises(CumulusCIException):
            task._get_destructive_changes()

    def test_dry_run(self):
        project_config = create_project_config()
        task = create_task(
            UninstallPackagedIncremental,
            {"dry_run": True},
            project_config,
        )
        task._get_destructive_changes = mock.Mock(return_value="foo")
        task.api_class = mock.Mock()
        task.logger = mock.Mock()

        task()
        assert task._get_api() is None
        task.logger.info.assert_has_calls([mock.call("foo")])
        task.api_class.assert_not_called()
