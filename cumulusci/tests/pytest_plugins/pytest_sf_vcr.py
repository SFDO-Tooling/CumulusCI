"""Salesforce customizations of VCR

Hides session IDs and OrgIDs.
Generally hides all request and response headers to save space in our repo.

Records transactions if there is an org specified and does not if there is not.
"""

import re

from .pytest_sf_orgconnect import sf_pytest_orgname


def simplify_body(request_or_response_body):
    decoded = request_or_response_body.decode("utf-8")
    if "<sessionId>" in decoded:
        decoded = re.sub(
            r"<sessionId>.*</sessionId>",
            "<sessionId>**Elided**</sessionId>",
            decoded,
        )
    decoded = re.sub(r"001[\w\d]{15,18}", "001ACCOUNTID", decoded)
    return decoded.encode()


def sf_before_record_request(request):
    if request.body:
        request.body = simplify_body(request.body)
    request.uri = re.sub(
        r"//.*.my.salesforce.com", "//orgname.my.salesforce.com", request.uri
    )
    request.uri = re.sub(
        r"//.*\d+.*.salesforce.com/", "//orgname.my.salesforce.com/", request.uri
    )
    request.uri = re.sub(r"00D[\w\d]{15,18}", "Organization/ORGID", request.uri)

    request.headers = {"Request-Headers": "Elided"}

    return request


# junk_headers = ["Public-Key-Pins-Report-Only", ]
def sf_before_record_response(response):
    response["headers"] = {"Response-Headers": "Elided"}
    if response.get("body"):
        response["body"]["string"] = simplify_body(response["body"]["string"])
    return response


def vcr_config(request):
    "Fixture for configuring VCR"

    orgname = sf_pytest_orgname(request)

    # https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes
    if orgname:
        record_mode = "once"
    else:
        record_mode = "none"

    return {
        "record_mode": record_mode,
        "decode_compressed_response": True,
        "before_record_response": sf_before_record_response,
        "before_record_request": sf_before_record_request,
        # this is redundant, but I guess its a from of
        # security in-depth
        "filter_headers": [
            "Authorization",
            "Cookie",
            "Public-Key-Pins-Report-Only",
            "Last-Modified",
        ],
    }


_version_string = re.compile(r"/v\d\d.0/")


def _noversion(s):
    if s:
        s = str(s, "utf-8") if isinstance(s, bytes) else s
        s = _version_string.sub(r"/vxx.0/", s)
        s = re.sub(r"/00D[\w\d]{10,20}", "/ORGID", s)
        s = re.sub(r".com//", r".com/", s)
        return s


def explain_mismatch(r1, r2):
    for a, b in zip(r1, r2):
        if a != b:
            print("MISMATCH\n\t", a, "\n!=\n\t", b)
    assert False
    return False


def salesforce_matcher(r1, r2):
    summary1 = (r1.method, _noversion(r1.uri), _noversion(r1.body))
    summary2 = (r2.method, _noversion(r2.uri), _noversion(r2.body))
    # uncomment explain_mismatch if you need to debug.
    # otherwise it will generate a lot of noise, even when things
    # are working properlly
    assert summary1 == summary2  # or explain_mismatch(summary1, summary2)


def salesforce_vcr(vcr):
    vcr.register_matcher("Salesforce Matcher", salesforce_matcher)
    vcr.match_on = ["Salesforce Matcher"]
    return vcr


salesforce_vcr.__doc__ = __doc__
