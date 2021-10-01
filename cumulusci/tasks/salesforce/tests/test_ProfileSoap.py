# from unittest import mock

import unittest

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.salesforce_api.exceptions import MetadataApiError
from cumulusci.tasks.salesforce.profiles import CreateBlankProfile

from .util import create_task

REQUEST_JSON = {
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
}

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


class TetstCreateBlankProfile(unittest.TestCase):
    @responses.activate
    def test_run_task_success(self):
        task = create_task(
            CreateBlankProfile,
            {
                "license": "Foo",
                "license_id": "",
                "name": "",
                "description": "",
            },
        )

        responses.add(
            responses.GET,
            "https://test.salesforce.com/services/data/v52.0/query/",
            json=REQUEST_JSON,
        )
        responses.add(
            responses.POST,
            "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
            RESPONSE_SUCCESS,
        )
        result = task._run_task()
        self.assertEqual("001R0000029IyDPIA0", result)

    @responses.activate
    def test_run_task_fault(self):
        task = create_task(
            CreateBlankProfile,
            {
                "license": "Foo",
                "license_id": "",
                "name": "",
                "description": "",
            },
        )

        responses.add(
            responses.GET,
            "https://test.salesforce.com/services/data/v52.0/query/",
            json=REQUEST_JSON,
        )
        responses.add(
            responses.POST,
            "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
            RESPONSE_FAULT,
        )
        with pytest.raises(MetadataApiError) as e:
            task._run_task()

        assert "Invalid Session ID found" in str(e)

    @responses.activate
    def test_run_task_field_error(self):
        task = create_task(
            CreateBlankProfile,
            {
                "license": "Foo",
                "license_id": "",
                "name": "",
                "description": "",
            },
        )

        responses.add(
            responses.GET,
            "https://test.salesforce.com/services/data/v52.0/query/",
            json=REQUEST_JSON,
        )
        responses.add(
            responses.POST,
            "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
            RESPONSE_ERROR_FIELD,
        )

        with pytest.raises(MetadataApiError) as e:
            task._run_task()
        assert "The profile name is already in use: Name" in str(e)

    @responses.activate
    def test_run_task_error(self):
        task = create_task(
            CreateBlankProfile,
            {
                "license": "Foo",
                "license_id": "",
                "name": "",
                "description": "",
            },
        )

        responses.add(
            responses.GET,
            "https://test.salesforce.com/services/data/v52.0/query/",
            json=REQUEST_JSON,
        )
        responses.add(
            responses.POST,
            "https://test.salesforce.com/services/Soap/u/53.0/ORG_ID",
            RESPONSE_ERROR,
        )

        with pytest.raises(MetadataApiError) as e:
            task._run_task()
        assert "INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY" in str(e)

    def test_task_options_error(self):
        with pytest.raises(TaskOptionsError):
            create_task(
                CreateBlankProfile,
                {
                    "name": "Foo",
                    "description": "Foo",
                },
            )
