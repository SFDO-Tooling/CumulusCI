# from unittest import mock

import pytest
import responses

from cumulusci.core.exceptions import TaskOptionsError
from cumulusci.tasks.salesforce.profiles import CreateBlankProfile

from .util import create_task

# from responses import query_params_matcher
CREATE_PROFILE = """<?xml version="1.0" encoding="utf-8"?>
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:urn="urn:partner.soap.sforce.com" xmlns:urn1="urn:sobject.partner.soap.sforce.com">
  <soapenv:Header>
    <urn:SessionHeader>
      <urn:sessionId>###SESSION_ID###</urn:sessionId>
    </urn:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <urn:create>
      <urn:sObjects xsi:type="urn1:Profile" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
        <Name>{name}</Name>
        <Description>{description}</Description>
        <UserLicenseId>{license_id}</UserLicenseId>
      </urn:sObjects>
    </urn:create>
  </soapenv:Body>
</soapenv:Envelope>"""


@responses.activate
def test_run_task():
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
    )
    task._run_task()
    assert len(responses.calls) == 2


# pytest --vcr-record=new_episodes --org qa
# @pytest.mark.vcr()
def test_task_options_error():
    with pytest.raises(TaskOptionsError):
        create_task(
            CreateBlankProfile,
            {
                "name": "Foo",
                "description": "Foo",
            },
        )
