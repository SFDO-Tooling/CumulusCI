"""Salesforce customizations of VCR

Hides session IDs and OrgIDs.
Generally hides all request and response headers to save space in our repo.

Records transactions if there is an org specified and does not if there is not.
"""

import re

from .pytest_sf_orgconnect import sf_pytest_orgname


def sf_before_record_cb(request):
    if request.body and "<sessionId>" in request.body.decode():
        request.body = re.sub(
            r"<sessionId>.*</sessionId>",
            "<sessionId>**Elided**</sessionId>",
            request.body.decode(),
        ).encode()
    request.uri = re.sub(
        r"//.*.my.salesforce.com", "//orgname.salesforce.com", request.uri
    )
    request.uri = re.sub(
        r"//.*\d+.*.salesforce.com/", "//orgname.salesforce.com/", request.uri
    )
    request.uri = re.sub(r"00D[\w\d]{15,18}", "Organization/ORGID", request.uri)

    request.headers = {"Request-Headers": "Elided"}

    return request


# junk_headers = ["Public-Key-Pins-Report-Only", ]
def sf_before_record_response(response):
    response["headers"] = {"Response-Headers": "Elided"}
    return response


def vcr_config(request):
    "Fixture for configuring VCR"

    orgname = sf_pytest_orgname(request)

    if orgname:
        record_mode = "all"
    else:
        record_mode = "none"

    return {
        "record_mode": record_mode,
        "decode_compressed_response": True,
        "before_record_response": sf_before_record_response,
        "before_record_request": sf_before_record_cb,
        # this is redundant, but I guess its a from of
        # security in-depth
        "filter_headers": [
            "Authorization",
            "Cookie",
            "Public-Key-Pins-Report-Only",
            "Last-Modified",
        ],
    }


def salesforce_matcher(r1, r2):
    summary1 = (r1.method, r1.uri, r1.body)
    summary2 = (r2.method, r2.uri, r2.body)
    assert summary1 == summary2


def salesforce_vcr(vcr):
    vcr.register_matcher("Salesforce Matcher", salesforce_matcher)
    vcr.match_on = ["Salesforce Matcher"]
    return vcr


salesforce_vcr.__doc__ = __doc__
