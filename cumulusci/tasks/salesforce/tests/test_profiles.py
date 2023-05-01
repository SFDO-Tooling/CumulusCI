import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.tasks.salesforce.profiles import CreateBlankProfile

from .util import create_task

RESPONSE_FAULT = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:sf="urn:fault.partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<soapenv:Body>
    <soapenv:Fault>
        <faultcode>sf:INVALID_SESSION_ID</faultcode>
        <faultstring>INVALID_SESSION_ID: Invalid Session ID found in SessionHeader: Illegal Session</faultstring>
        <detail>
        <sf:UnexpectedErrorFault xsi:type="sf:UnexpectedErrorFault">
            <sf:exceptionCode>INVALID_SESSION_ID</sf:exceptionCode>
            <sf:exceptionMessage>Invalid Session ID found in SessionHeader: Illegal Session</sf:exceptionMessage>
        </sf:UnexpectedErrorFault>
        </detail>
    </soapenv:Fault>
</soapenv:Body>
</soapenv:Envelope>"""

RESPONSE_ERROR = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<soapenv:Body>
    <createResponse>
        <result>
        <errors>
            <message>insufficient access rights on cross-reference id</message>
            <statusCode>INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY</statusCode>
        </errors>
        <id xsi:nil="true"/>
        <success>false</success>
        </result>
    </createResponse>
</soapenv:Body>
</soapenv:Envelope>"""

RESPONSE_ERROR_FIELD = """<?xml version="1.0" encoding="UTF-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:partner.soap.sforce.com" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
<soapenv:Header>
    <LimitInfoHeader>
        <limitInfo>
        <current>43</current>
        <limit>5000000</limit>
        <type>API REQUESTS</type>
        </limitInfo>
    </LimitInfoHeader>
</soapenv:Header>
<soapenv:Body>
    <createResponse>
        <result>
        <errors>
            <fields>Name</fields>
            <message>The profile name is already in use: Name</message>
            <statusCode>FIELD_INTEGRITY_EXCEPTION</statusCode>
        </errors>
        <id xsi:nil="true" />
        <success>false</success>
        </result>
    </createResponse>
</soapenv:Body>
</soapenv:Envelope>"""

RESPONSE_SUCCESS = """<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns="urn:partner.soap.sforce.com">
<soapenv:Body>
    <createResponse>
        <result>
        <id>001R0000029IyDPIA0</id>
        <success>true</success>
        </result>
    </createResponse>
</soapenv:Body>
</soapenv:Envelope>"""


@responses.activate
def test_run_task_success():
    query_url = "https://test.salesforce.com/services/data/v53.0/query/"

    task = create_task(
        CreateBlankProfile,
        {
            "license": "Foo",
            "name": "Test Profile Name",
            "description": "Have fun stormin da castle",
        },
    )
    task.org_config._latest_api_version = "53.0"

    responses.add(
        responses.GET,
        query_url,
        json={
            "done": True,
            "totalSize": 1,
            "records": [
                {
                    "attributes": {
                        "type": "UserLicense",
                        "url": "/services/data/v53.0/sobjects/UserLicense/10056000000VGjUAAW",
                    },
                    "Id": "10056000000VGjUAAW",
                    "Name": "Salesforce",
                }
            ],
        },
    )
    responses.add(
        responses.POST,
        "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
        RESPONSE_SUCCESS,
    )
    result = task._run_task()
    assert result == "001R0000029IyDPIA0"
    assert responses.calls[0].request.params == {
        "q": "SELECT Id, Name FROM UserLicense WHERE Name = 'Foo' LIMIT 1"
    }
    soap_body = responses.calls[1].request.body
    assert "<Name>Test Profile Name</Name>" in str(soap_body)
    assert "<UserLicenseId>10056000000VGjUAAW</UserLicenseId>" in str(soap_body)
    assert "<Description>Have fun stormin da castle</Description>" in str(soap_body)


@responses.activate
def test_run_task_fault():
    task = create_task(
        CreateBlankProfile,
        {
            "license_id": "10056000000VGjUAAW",
            "name": "Test Profile",
            "description": "This is the description",
        },
    )
    task.org_config._latest_api_version = "53.0"

    responses.add(
        responses.POST,
        "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
        RESPONSE_FAULT,
    )
    with pytest.raises(MetadataApiError) as e:
        task._run_task()

    assert "Invalid Session ID found" in str(e)


@responses.activate
def test_run_task_field_error():
    task = create_task(
        CreateBlankProfile,
        {
            "license_id": "10056000000VGjUAAW",
            "name": "Test Profile",
            "description": "This is the description",
        },
    )
    task.org_config._latest_api_version = "53.0"
    responses.add(
        responses.POST,
        "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
        RESPONSE_ERROR_FIELD,
    )

    with pytest.raises(MetadataApiError) as e:
        task._run_task()
    assert "The profile name is already in use: Name" in str(e)


@responses.activate
def test_run_task_error():
    task = create_task(
        CreateBlankProfile,
        {
            "license_id": "10056000000VGjUAAW",
            "name": "Test Profile",
            "description": "This is the description",
        },
    )
    task.org_config._latest_api_version = "53.0"

    responses.add(
        responses.POST,
        "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
        RESPONSE_ERROR,
    )

    with pytest.raises(MetadataApiError) as e:
        task._run_task()
    assert "insufficient access rights on cross-reference id" in str(e)


def test_task_options_error():
    with pytest.raises(TaskOptionsError):
        create_task(
            CreateBlankProfile,
            {
                "name": "Foo",
                "description": "Foo",
            },
        )
