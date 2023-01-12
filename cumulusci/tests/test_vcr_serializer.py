from pathlib import Path

import yaml

from cumulusci.tests.pytest_plugins.pytest_sf_vcr_serializer import (
    CompressionVCRSerializer,
    RequestResponseReplacement,
    _compress_in_place,
)
from cumulusci.tests.pytest_plugins.vcr_string_compressor import (
    StringToTemplateCompressor,
)


class TestVCRSerializer:
    def test_compress_inclusions(self):
        serialized_request = "{'method': 'GET', 'uri': 'https://orgname.my.salesforce.com/services/data/vxx.0/sobjects/Organization/00D0xORGID00000000', 'body': None, 'headers': {'Request-Headers': ['Elided']}}"
        saved_responses = {
            serialized_request: RequestResponseReplacement(
                request=...,
                response=...,
                replacement_file="GET_sobjects_Organization.yaml",
            )
        }
        d = {
            "interactions": [
                {
                    "request": {
                        "method": "GET",
                        "uri": "https://orgname.my.salesforce.com/services/data/vxx.0/sobjects/Organization/00D0xORGID00000000",
                        "body": None,
                        "headers": {"Request-Headers": ["Elided"]},
                    },
                    "response": {"Blah"},
                }
            ],
            "version": 42,
        }
        x = _compress_in_place(d, saved_responses, StringToTemplateCompressor({}))
        assert x == {
            "interactions": [{"include_file": "GET_sobjects_Organization.yaml"}],
            "version": 42,
        }

    def test_compress_duplications(self):
        d = {
            "interactions": [
                {
                    "request": {
                        "method": "GET",
                        "uri": "https://orgname.my.salesforce.com/services/data/vxx.0/sobjects/Organization/00D0xORGID00000000",
                        "body": None,
                        "headers": {"Request-Headers": ["Elided"]},
                    },
                    "response": {"Blah": "Blah"},
                },
                {
                    "request": {
                        "method": "GET",
                        "uri": "https://orgname.my.salesforce.com/services/data/vxx.0/sobjects/Organization/00D0xORGID00000000",
                        "body": None,
                        "headers": {"Request-Headers": ["Elided"]},
                    },
                    "response": {"Blah": "Blah"},
                },
            ],
            "version": 42,
        }

        x = _compress_in_place(d, {}, StringToTemplateCompressor({}))
        assert x is d
        assert x["interactions"][0] is x["interactions"][1]

        print(yaml.dump(x))
        assert yaml.dump(x).strip() == EXPECTED.strip()

    def test_compress_file(self, cumulusci_test_repo_root):
        directory = cumulusci_test_repo_root / "cumulusci/tests/shared_cassettes"
        serializer = CompressionVCRSerializer(directory)
        file_to_compress = Path("cumulusci/tests/uncompressed_cassette.yaml")
        with file_to_compress.open() as f:
            data = yaml.safe_load(f)

        as_string = serializer.serialize(data)
        assert as_string.strip() == EXPECTED2.strip()


EXPECTED = """
interactions:
- &id001
  request:
    body: null
    headers:
      Request-Headers:
      - Elided
    method: GET
    uri: https://orgname.my.salesforce.com/services/data/vxx.0/sobjects/Organization/00D0xORGID00000000
  response:
    Blah: Blah
- *id001
version: 42""".strip()

EXPECTED2 = """
version: 1
interactions:
- &id001
  include_file: GET_sobjects_Global_describe.yaml
- include_file: GET_sobjects_Account_describe.yaml
- *id001
- request:
    method: POST
    uri: https://orgname.my.salesforce.com/services/async/vxx.0/job/75023000003Rs2qAAC
    body: <jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload"><state>Closed</state></jobInfo>
    headers:
      Request-Headers:
      - Elided
  response:
    status:
      code: 200
      message: OK
    headers:
      Content-Type:
      - application/xml
      Others: Elided
    body:
      string:
        include_template: jobInfo_insert_xml.tpl
        vars:
          id: 75023000003Rs2qAAC
          creator: 00523000002KbrQAAS
          cdate: '2022-03-30T07:57:00.000Z'
          smts: '2022-03-30T07:57:00.000Z'
          state: Closed
          qdbatches: '1'"""
