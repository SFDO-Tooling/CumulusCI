from cumulusci.tests.pytest_plugins.pytest_sf_vcr_serializer import (
    RequestResponseReplacement,
    _compress,
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
        x = _compress(d, saved_responses)
        assert x == {
            "interactions": [{"include_file": "GET_sobjects_Organization.yaml"}],
            "version": 42,
        }
