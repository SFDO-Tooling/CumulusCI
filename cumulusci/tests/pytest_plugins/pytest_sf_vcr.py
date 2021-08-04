"""Salesforce customizations of VCR

Hides session IDs and OrgIDs.
Generally hides all request and response headers to save space in our repo.

Records transactions if there is an org specified and does not if there is not.
"""

import re
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path

import pytest
from vcr import cassette


def simplify_body(request_or_response_body):
    decoded = request_or_response_body.decode("utf-8")
    decoded = _cleanup(decoded)
    # if "GeocodeAccuracy" in decoded:
    #     breakpoint()

    return decoded.encode()


replacements = [
    (r"/v?\d\d.0/", r"/vxx.0/"),
    (r"/00D[\w\d]{12,15}", "/00D0xORGID00000000"),
    (r'"00D[\w\d]{12,15}"', '"00D0xORGID00000000"'),
    (r".com//", r".com/"),
    (r"ersion>\d\d.0<", r"ersion>vxx.0<"),
    (r"<sessionId>.*</sessionId>", r"<sessionId>**Elided**</sessionId>"),
    (r"001[\w\d]{12,15}", "0010xACCOUNTID0000"),
    (r"//.*.my.salesforce.com", "//orgname.my.salesforce.com"),
    (r"//.*\d+.*.salesforce.com/", "//orgname.my.salesforce.com/"),
    (
        r"202\d-\d\d-\d\dT\d\d:\d\d\:\d\d.\d\d\d\+0000",
        "2021-01-01T01:02:01.000+0000",
    ),
    (r'"005[\w\d]{12,15}"', '"0050xUSERID0000000"'),
    (r'"InstanceName" : "[A-Z]{2,4}\d{1,4}",', '"InstanceName" : "CS420",'),
    (r"<id>0.*<\/id>", lambda m: "<id>0ANID</id>"),
    (
        r"<asyncProcessId>0.*<\/asyncProcessId>",
        lambda m: "<asyncProcessId>0ANAPPID</asyncProcessId>",
    ),
    (r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\dZ", "2021-01-03T01:11:11.420Z"),
    (r"/User/005[\w\d]{12,15}", "/User/0050xUSERID0000000"),
    (r"<lastModifiedById>005[\w\d]{12,15}", "<lastModifiedById>005USERID"),
]

replacements = [
    (re.compile(pattern), replacement) for (pattern, replacement) in replacements
]


RECORDING = ContextVar("RECORDING", default=True)
READING = ContextVar("READING", default=True)


@contextmanager
def set_mode(mode, value):
    orig = mode.get()
    mode.set(value)
    try:
        yield
    finally:
        mode.set(orig)


@pytest.fixture(scope="function")
def vcr_cassette_path(vcr_cassette_dir, vcr_cassette_name):
    return Path(vcr_cassette_dir, vcr_cassette_name + ".yaml")


@pytest.fixture(autouse=True)
def configure_recording_mode(
    request,
    user_requested_network_access,
    vcr_cassette_path,
    user_requested_cassette_replacement,
):
    recording_mode = RECORDING.get()
    reading_mode = READING.get()
    if (
        user_requested_network_access
        and vcr_cassette_path.exists()
        and user_requested_cassette_replacement
    ):
        vcr_cassette_path.unlink()
        recording_mode = True
        reading_mode = "irrelevant"  # reading from missing file
    elif user_requested_network_access and vcr_cassette_path.exists():
        # user wants to keep existing cassette, so disable VCR usage entirely, like:
        # https://github.com/ktosiek/pytest-vcr/blob/08482cf0724697c14b63ad17752a0f13f7670add/pytest_vcr.py#L56
        recording_mode = False
        reading_mode = False
    elif user_requested_network_access:
        recording_mode = True
        reading_mode = "irrelevant"  # file doesn't exist, so reading missing file
    else:
        recording_mode = False
        reading_mode = True

    with set_mode(RECORDING, recording_mode), set_mode(READING, reading_mode):
        yield


def sf_before_record_request(http_request):

    if not (READING.get() or RECORDING.get()):
        return None
    if http_request.body:
        http_request.body = simplify_body(http_request.body)
    http_request.uri = _cleanup(http_request.uri)

    http_request.headers = {"Request-Headers": "Elided"}

    return http_request


# junk_headers = ["Public-Key-Pins-Report-Only", ]
def sf_before_record_response(response):
    response["headers"] = {"Response-Headers": "Elided"}
    if response.get("body"):
        response["body"]["string"] = simplify_body(response["body"]["string"])
    return response


def vcr_config(request, user_requested_network_access):
    "Fixture for configuring VCR"

    # https://vcrpy.readthedocs.io/en/latest/usage.html#record-modes
    if user_requested_network_access:
        record_mode = "new_episodes"  # should this be once?
    else:
        record_mode = "none"

    return {
        "record_mode": record_mode,
        "decode_compressed_response": True,
        "before_record_response": sf_before_record_response,
        "before_record_request": sf_before_record_request,
        # this is redundant, but I guess its a form of
        # security in-depth
        "filter_headers": [
            "Authorization",
            "Cookie",
            "Public-Key-Pins-Report-Only",
            "Last-Modified",
        ],
    }


def _cleanup(s: str):
    if s:
        s = str(s, "utf-8") if isinstance(s, bytes) else s
        for pattern, replacement in replacements:
            s = pattern.sub(replacement, s)
        return s


def explain_mismatch(r1, r2):
    print("CURRENT", r1, "\nTAPED", r2)
    for a, b in zip(r1, r2):
        if a != b:
            print("\nMISMATCH\n\t Current:", a, "\n!=\n\tTaped:   ", b)
            break
    return False


def salesforce_matcher(r1, r2, should_explain=False):
    summary1 = (r1.method, _cleanup(r1.uri), _cleanup(r1.body))
    summary2 = (r2.method, _cleanup(r2.uri), _cleanup(r2.body))
    # uncomment explain_mismatch if you need to debug.
    # otherwise it will generate a lot of noise, even when things
    # are working properly
    if summary1 != summary2:
        if should_explain:
            return None
            # return explain_mismatch(summary1, summary2)
        else:
            assert summary1 == summary2

    return True


def salesforce_vcr(vcr):
    vcr.register_matcher("Salesforce Matcher", salesforce_matcher)
    vcr.match_on = ["Salesforce Matcher"]
    return vcr


salesforce_vcr.__doc__ = __doc__

orig_contains = cassette.Cassette.__contains__


# better error handling than the built-in VCR stuff
def __contains__(self, request):
    """Return whether or not a request has been stored"""
    if orig_contains(self, request):
        return True

    # otherwise give a helpful warning
    for index, response in self._responses(request):
        if self.play_counts[index] != 0:
            raise AssertionError(
                "SALESFORCE VCR Error: Request matched but response had already been used ****"
            )

    for index, (stored_request, response) in enumerate(self.data):
        salesforce_matcher(request, stored_request, should_explain=True)

    return False


cassette.Cassette.__contains__ = __contains__
