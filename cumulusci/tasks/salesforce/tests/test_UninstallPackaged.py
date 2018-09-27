import io
import mock
import unittest
import zipfile

from cumulusci.tasks.salesforce import UninstallPackaged
from cumulusci.tests.util import create_project_config
from .util import create_task


class TestUninstallPackaged(unittest.TestCase):
    @mock.patch("cumulusci.salesforce_api.metadata.ApiRetrievePackaged.__call__")
    def test_get_destructive_changes(self, ApiRetrievePackaged):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        task = create_task(UninstallPackaged, {}, project_config)
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "TestPackage/objects/Test__c.object",
            '<?xml version="1.0" encoding="UTF-8"?><root />',
        )
        ApiRetrievePackaged.return_value = zf
        result = task._get_destructive_changes()
        self.assertEqual(
            """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
    <version>43.0</version>
</Package>""",
            result,
        )
