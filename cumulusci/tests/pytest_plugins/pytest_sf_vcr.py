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
        "//cs.*.salesforce.com", "//podname.salesforce.com", request.uri
    )
    request.uri = re.sub(
        "Organization/00D3B000000F7hh", "Organization/ORGID", request.uri
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
