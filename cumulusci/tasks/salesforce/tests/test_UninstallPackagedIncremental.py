import io
from unittest import mock
import os
import unittest
import zipfile

from cumulusci.tasks.salesforce import UninstallPackagedIncremental
from cumulusci.tests.util import create_project_config
from cumulusci.utils import temporary_dir
from .util import create_task


class TestUninstallPackagedIncremental(unittest.TestCase):
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
                    "ignore_types": ["CustomObjectTranslation", "RecordType"],
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
            self.assertEqual(
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
</Package>""",
                result,
            )
