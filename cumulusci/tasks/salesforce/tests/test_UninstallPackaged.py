import io
import zipfile
from unittest import mock

import pytest
import responses

from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.tasks.salesforce import UninstallPackaged
from cumulusci.tests.util import create_project_config

from .util import create_task


class TestUninstallPackaged:
    @mock.patch("cumulusci.salesforce_api.metadata.ApiRetrievePackaged.__call__")
    def test_get_destructive_changes(self, ApiRetrievePackaged):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        project_config.config["project"]["package"]["api_version"] = "43.0"
        task = create_task(UninstallPackaged, {}, project_config)
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
        zf.close()

    @responses.activate
    def test_error_handling(self):
        project_config = create_project_config()
        project_config.config["project"]["package"]["name"] = "TestPackage"
        project_config.config["project"]["package"]["api_version"] = "43.0"
        task = create_task(UninstallPackaged, {}, project_config)

        responses.add(
            method=responses.POST,
            url="https://test.salesforce.com/services/Soap/m/43.0/ORG_ID",
            body="""<?xml version="1.0" encoding="UTF-8"?>
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns="http://soap.sforce.com/2006/04/metadata" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <soapenv:Body><checkRetrieveStatusResponse><result><done>true</done>
        <errorMessage>INVALID_CROSS_REFERENCE_KEY: No package named &apos;Abacus&apos; found</errorMessage>
        <errorStatusCode>UNKNOWN_EXCEPTION</errorStatusCode><id>09S6g000007KGwVEAW</id><status>Failed</status>
        <success>false</success><zipFile xsi:nil="true"/></result>
        </checkRetrieveStatusResponse></soapenv:Body></soapenv:Envelope>""",
            status=200,
            content_type="text/xml; charset=utf-8",
        )

        with pytest.raises(MetadataApiError) as e:
            task()
        assert "No package" in str(e.value)
