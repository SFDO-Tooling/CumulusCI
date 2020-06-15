import io
from unittest import mock
import zipfile


import pytest

from cumulusci.tasks.salesforce import UninstallPackaged
from cumulusci.tests.util import create_project_config
from .util import create_task as create_mock_task
from cumulusci.salesforce_api.exceptions import MetadataApiError


class TestUninstallPackaged:
    @mock.patch("cumulusci.salesforce_api.metadata.ApiRetrievePackaged.__call__")
    def test_get_destructive_changes(self, ApiRetrievePackaged):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        project_config.config["project"]["package"]["api_version"] = "43.0"
        task = create_mock_task(UninstallPackaged, {}, project_config)
        zf = zipfile.ZipFile(io.BytesIO(), "w")
        zf.writestr(
            "TestPackage/objects/Test__c.object",
            '<?xml version="1.0" encoding="UTF-8"?><root />',
        )
        ApiRetrievePackaged.return_value = zf
        result = task._get_destructive_changes()
        assert (
            """<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>Test__c</members>
        <name>CustomObject</name>
    </types>
    <version>43.0</version>
</Package>"""
            == result
        )

    @pytest.mark.vcr()
    def test_error_handling(self, create_task):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        project_config.config["project"]["package"]["api_version"] = "43.0"
        task = create_task(UninstallPackaged, {"package": "xyzzy"}, project_config)

        with pytest.raises(MetadataApiError) as e:
            task()
        assert "No package" in str(e.value)
        assert "xyzzy" in str(e.value)
