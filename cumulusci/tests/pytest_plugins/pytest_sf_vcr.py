import re

from .pytest_sf_orgconnect import sf_pytest_orgname


def sf_before_record_cb(request):
    if request.body and "<sessionId>" in request.body.decode():
        request.body = re.sub(
            "<sessionId>.*</sessionId>",
            "<sessionId>**Elided**</sessionId>",
            request.body.decode(),
        ).encode()
    request.uri = re.sub(
        "//.*.my.salesforce.com", "//orgname.salesforce.com", request.uri
    )
    request.uri = re.sub(
        "//cs.*.salesforce.com/", "//podname.salesforce.com/", request.uri
    )
    request.uri = re.sub("Organization/00.*", "Organization/ORGID", request.uri)

    # note that this line has a leading slash in one place and not the other
    # this is the only way it seems to work. I don't know why.
    request.uri = re.sub(
        "/services/Soap/m/48.0/00.*", "services/Soap/m/48.0/ORGID", request.uri
    )

    request.headers = {"Request-Headers": "Elided"}

    return request


# junk_headers = ["Public-Key-Pins-Report-Only", ]
def sf_before_record_response(response):
    # for header in junk_headers:
    #     if response["headers"].get(header):
    #         del response["headers"][header]
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
    print(summary1, summary2, summary1 == summary2)
    assert summary1 == summary2


def salesforce_vcr(vcr):
    vcr.register_matcher("Salesforce Matcher", salesforce_matcher)
    vcr.match_on = ["Salesforce Matcher"]
    return vcr
