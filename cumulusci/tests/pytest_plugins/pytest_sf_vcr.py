"""Salesforce customizations of VCR

Hides session IDs and OrgIDs.
Generally hides all request and response headers to save space in our repo.

Records transactions if there is an org specified and does not if there is not.
"""

import re
from functools import partial
from pathlib import Path
from string import hexdigits

import pytest
from vcr import cassette
from vcr.util import read_body

from cumulusci.core.enums import StrEnum

from .pytest_sf_vcr_serializer import CompressionVCRSerializer

# Byte values that are valid hexadecimal digits, used by the chunked-transfer
# de-framer below (mirrors vcr.matchers._HEXDIG_CODE_POINTS).
_HEXDIG_CODE_POINTS = {ord(c) for c in hexdigits}


def _body_to_bytes(body):
    """Normalize a VCR request/response body to bytes.

    urllib3 2.x can hand vcrpy a streaming iterator of chunks rather than a
    single bytes object, so coerce every supported shape to bytes.
    """
    if isinstance(body, bytes):
        return body
    if isinstance(body, bytearray):
        return bytes(body)
    if isinstance(body, str):
        return body.encode("utf-8")
    if hasattr(body, "read"):  # file-like
        return _body_to_bytes(body.read())
    chunks = []
    for chunk in body:  # iterator of byte/str/int chunks (urllib3 2.x streaming)
        if isinstance(chunk, int):
            # A bytes iterator (iter(b"...")) yields individual byte *values*;
            # bytes(int) would emit N zero-bytes, so wrap the value instead.
            chunks.append(bytes((chunk,)))
        elif isinstance(chunk, str):
            chunks.append(chunk.encode("utf-8"))
        else:
            chunks.append(bytes(chunk))
    return b"".join(chunks)


def simplify_body(request_or_response_body):
    decoded = _body_to_bytes(request_or_response_body).decode("utf-8")
    decoded = _cleanup(decoded)

    return decoded.encode()


class RecordingMode(StrEnum):
    RECORD = "Recording"
    READ = "Reading"
    DISABLE = "Disabled"


replacements = [
    (r"/v?\d\d.0/", r"/vxx.0/"),
    (r"/00D[\w\d]{12,15}", "/00D0xORGID00000000"),
    (r'"00D[\w\d]{12,15}"', '"00D0xORGID00000000"'),
    (r".com//", r".com/"),
    (r"ersion>\d\d.0<", r"ersion>vxx.0<"),
    (r"<sessionId>.*</sessionId>", r"<sessionId>**Elided**</sessionId>"),
    # (r"001[\w\d]{12,15}", "0010xACCOUNTID0000"),
    (r"//.*.my.salesforce.com", "//orgname.my.salesforce.com"),
    (r"//.*\d+.*.salesforce.com/", "//orgname.my.salesforce.com/"),
    # (
    #     r"202\d-\d\d-\d\dT\d\d:\d\d\:\d\d.\d\d\d\+0000",
    #     "2021-01-01T01:02:01.000+0000",
    # ),
    # (r'"005[\w\d]{12,15}"', '"0050xUSERID0000000"'),
    (r'"InstanceName" : "[A-Z]{2,4}\d{1,4}",', '"InstanceName" : "CS420",'),
    # (r"<id>0.*<\/id>", "<id>0ANAPPID{}</id>"),  # replace SOAP message IDs.
    (
        r"<asyncProcessId>0.*<\/asyncProcessId>",
        "<asyncProcessId>0ANAPPID</asyncProcessId>",
    ),
    # in case we ever want to normalize dates again, here is how we would do it.
    # (r"\d\d\d\d-\d\d-\d\dT\d\d:\d\d:\d\d.\d\d\dZ", "2021-01-03T01:11:11.420Z"),
    # (r"/User/005[\w\d]{12,15}", "/User/0050xUSERID0000000"),
    # (r"<lastModifiedById>005[\w\d]{12,15}", "<lastModifiedById>005USERID"),
]

replacements = [
    (re.compile(pattern), replacement) for (pattern, replacement) in replacements
]


@pytest.fixture(scope="function")
def vcr_cassette_path(vcr_cassette_dir, vcr_cassette_name):
    return Path(vcr_cassette_dir, vcr_cassette_name + ".yaml")


class VcrState:
    recording: RecordingMode = RecordingMode.READ


@pytest.fixture(scope="session")
def vcr_state():
    return VcrState()


@pytest.fixture(autouse=True)
def configure_recording_mode(
    request,
    user_requested_network_access,
    vcr_cassette_path,
    user_requested_cassette_replacement,
    vcr_state,
    monkeypatch,
):
    recording_mode = vcr_state.recording
    if (
        user_requested_network_access
        and vcr_cassette_path.exists()
        and user_requested_cassette_replacement
    ):
        vcr_cassette_path.unlink()
        recording_mode = RecordingMode.RECORD
    elif user_requested_network_access and vcr_cassette_path.exists():
        # user wants to keep existing cassette, so disable VCR usage entirely, like:
        # https://github.com/ktosiek/pytest-vcr/blob/08482cf0724697c14b63ad17752a0f13f7670add/pytest_vcr.py#L59
        recording_mode = RecordingMode.DISABLE
    elif user_requested_network_access:
        recording_mode = RecordingMode.RECORD
    else:
        # reading
        recording_mode = RecordingMode.READ

    with monkeypatch.context() as m:
        m.setattr(vcr_state, "recording", recording_mode)
        yield


def sf_before_record_request(vcr_state, http_request):
    if vcr_state.recording == RecordingMode.DISABLE:
        return None
    if http_request.body:
        # urllib3 2.x can present the body as a one-shot/bytes iterator that
        # vcr.Request re-wraps on every ``.body`` access. Materialize it to bytes
        # once (clearing _was_iter/_was_file) so simplify_body operates on bytes
        # and repeated filter passes stay idempotent instead of re-corrupting it.
        _normalize_request_body(http_request)
        http_request.body = simplify_body(http_request.body)
    http_request.uri = _cleanup(http_request.uri)

    http_request.headers = {"Request-Headers": "Elided"}

    return http_request


def sf_before_record_response(response):
    response["headers"] = {
        "Content-Type": response["headers"].get("Content-Type", "None"),
        "Others": "Elided",
    }
    if response.get("body"):
        response["body"]["string"] = simplify_body(response["body"]["string"])
    return response


def vcr_config(request, user_requested_network_access, vcr_state):
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
        "before_record_request": partial(sf_before_record_request, vcr_state),
        # this is redundant, but I guess its a form of
        # security in-depth
        "filter_headers": [
            "Authorization",
            "Cookie",
            "Public-Key-Pins-Report-Only",
            "Last-Modified",
        ],
    }


@pytest.fixture(scope="function")
def bind_vcr_state(request, vcr_state):
    "Give the vcr_state object access to the request"
    vcr_state.request = request
    yield
    vcr_state.request = None


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


def _normalize_request_body(request):
    """Coerce a VCR request body to bytes once, caching it on the request.

    urllib3 2.x can present a request body as a one-shot iterator; the matcher
    runs repeatedly, so materialize and cache to keep matching stable.

    Two vcr.Request subtleties make this trickier than a plain ``_body_to_bytes``:

    * A body passed as ``iter(b"...")`` becomes a *bytes iterator* whose elements
      are ``int`` byte values, so vcr stores ``_body`` as a list of ints. vcr's
      ``read_body`` rebuilds that with ``bytes(list_of_ints)``; a naive per-chunk
      coercion would instead emit ``bytes(int)`` (zero-filled garbage).
    * vcr re-wraps file/iterator bodies with a fresh ``BytesIO``/``iter()`` on
      every ``.body`` access (see ``_was_file`` / ``_was_iter``). If those flags
      stay set, the cached bytes get re-wrapped on the next read. Clear them so
      subsequent reads return the cached bytes verbatim.
    """
    body = request.body
    if body is None or isinstance(body, (bytes, bytearray, str)):
        return body
    body = read_body(request)
    request._was_file = False
    request._was_iter = False
    request.body = body
    return body


def _dechunk_body(body):
    """Strip HTTP chunked-transfer framing from a request body, if present.

    urllib3 1.x baked chunk framing (``<hexlen>\\r\\n<data>\\r\\n ... 0\\r\\n\\r\\n``)
    into recorded bulk-API request bodies; urllib3 2.x sends the same logical
    bytes *unframed*. Canonicalizing both sides lets the original, proven
    cassettes replay unchanged instead of re-recording (vcrpy #734, fixed
    upstream in PR #739's built-in ``body`` matcher).

    We can't lean on vcrpy's built-in fix: it is header-gated on
    ``Transfer-Encoding: chunked`` and only runs when both requests resolve to
    the same transformer set, but ``salesforce_matcher`` elides headers and the
    framing is now asymmetric (taped=framed, live=unframed). So we de-frame
    unconditionally on both sides. This is a faithful port of
    ``vcr.matchers._dechunk`` (vendored rather than imported because it is a
    private symbol and we have an in-flight vcrpy major bump).

    Guard: anything that does not begin with hex digits followed by CRLF is
    assumed to be non-chunked and returned untouched, so a legitimate XML/JSON
    body is never corrupted.
    """
    if body is None:
        return body
    if isinstance(body, str):
        body = body.encode("utf-8")
    elif isinstance(body, bytearray):
        body = bytes(body)
    elif not isinstance(body, bytes):
        return body

    CHUNK_GAP = b"\r\n"
    body_len = len(body)
    chunks = []
    pos = 0
    while True:
        i = pos
        for i in range(pos, body_len):
            if body[i] not in _HEXDIG_CODE_POINTS:
                break
        if i == pos or body[i : i + len(CHUNK_GAP)] != CHUNK_GAP:
            if pos == 0:
                return body  # assume non-chunk data
            raise ValueError("Malformed chunked data")
        size_bytes = int(body[pos:i], 16)
        if size_bytes == 0:  # well-formed terminating chunk
            return b"".join(chunks)
        chunk_first = i + len(CHUNK_GAP)
        chunk_after_last = chunk_first + size_bytes
        if body[chunk_after_last : chunk_after_last + len(CHUNK_GAP)] != CHUNK_GAP:
            raise ValueError("Malformed chunked data")
        chunks.append(body[chunk_first:chunk_after_last])
        pos = chunk_after_last + len(CHUNK_GAP)


def _canonical_request_body(request):
    """Materialize (urllib3 2.x iterators) then de-frame a request body."""
    return _dechunk_body(_normalize_request_body(request))


def salesforce_matcher(r1, r2, should_explain=False):
    summary1 = (r1.method, _cleanup(r1.uri), _cleanup(_canonical_request_body(r1)))
    summary2 = (r2.method, _cleanup(r2.uri), _cleanup(_canonical_request_body(r2)))
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


@pytest.fixture(scope="session")
def salesforce_serializer(shared_vcr_cassettes):
    return CompressionVCRSerializer(shared_vcr_cassettes)


def salesforce_vcr(vcr, salesforce_serializer):
    vcr.register_matcher("Salesforce Matcher", salesforce_matcher)
    vcr.match_on = ["Salesforce Matcher"]
    vcr.register_serializer("Compression Serializer", salesforce_serializer)
    vcr.serializer = "Compression Serializer"
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
                f"SALESFORCE VCR Error: Request matched but response had already been used **** {request}"
            )

    for index, (stored_request, response) in enumerate(self.data):
        salesforce_matcher(request, stored_request, should_explain=True)

    return False


@pytest.fixture(
    scope="function",
)
def run_code_without_recording(
    request, vcr, user_requested_network_access, vcr_state, monkeypatch
):
    def really_run_code_without_recording(func):
        if user_requested_network_access:
            # Run the setup code, but don't record it
            with monkeypatch.context() as m:
                m.setattr(vcr_state, "recording", RecordingMode.DISABLE)
                return func()

    return really_run_code_without_recording


cassette.Cassette.__contains__ = __contains__
