import pytest
from vcr.request import Request

from cumulusci.tests.pytest_plugins.pytest_sf_vcr import (
    RecordingMode,
    _body_to_bytes,
    _normalize_request_body,
    salesforce_matcher,
    sf_before_record_request,
    simplify_body,
)


class _VcrState:
    """Minimal stand-in for the VcrState fixture used by the request filter."""

    recording = RecordingMode.READ


def test_simplify_body_accepts_bytes():
    assert simplify_body(b"hello world") == b"hello world"


def test_simplify_body_accepts_str():
    assert simplify_body("hello world") == b"hello world"


def test_simplify_body_accepts_list_iterator():
    # urllib3 2.x can hand vcrpy a streaming iterator of byte chunks
    # instead of a single bytes object (the cause of #3977's CI failures).
    assert simplify_body(iter([b"hel", b"lo"])) == b"hello"


def test_simplify_body_applies_cleanup_on_iterator():
    body = iter([b'{"id": "00D000000000000AAA"}'])
    result = simplify_body(body)
    assert b"00D0xORGID00000000" in result


def test_body_to_bytes_accepts_bytearray():
    assert _body_to_bytes(bytearray(b"hello")) == b"hello"


def test_body_to_bytes_accepts_file_like():
    import io

    assert _body_to_bytes(io.BytesIO(b"hello")) == b"hello"


def test_body_to_bytes_accepts_mixed_chunk_iterator():
    assert _body_to_bytes(iter([b"hel", "lo"])) == b"hello"


def test_body_to_bytes_accepts_bytes_iterator_of_ints():
    # iter(b"hello") yields *ints* (104, 101, ...). Naive per-chunk coercion
    # (bytes(int)) turns each into N zero-bytes, corrupting the body. This is the
    # urllib3 2.x bulk-upload shape that broke the two upsert cassettes.
    assert _body_to_bytes(iter(b"hello")) == b"hello"


def _req(body):
    return Request(
        "POST", "https://orgname.my.salesforce.com/services/data/v50.0/x", body, {}
    )


def test_salesforce_matcher_handles_iterator_body():
    # urllib3 2.x can deliver the live request body as a one-shot iterator.
    r1 = _req(iter([b'{"a": ', b"1}"]))
    r2 = _req(b'{"a": 1}')
    assert salesforce_matcher(r1, r2) is True


def test_salesforce_matcher_handles_bytes_iterator_body():
    # The real urllib3 2.x case: the live body arrives as a *bytes iterator*
    # (iter(b"...")), which vcr stores as a list of int byte-values. Naive
    # per-chunk coercion (bytes(int)) would corrupt this into zero-filled bytes.
    r1 = _req(iter(b'{"a": 1}'))
    r2 = _req(b'{"a": 1}')
    assert salesforce_matcher(r1, r2) is True


def test_normalize_request_body_caches_materialized_bytes():
    r = _req(iter([b"hel", b"lo"]))
    assert _normalize_request_body(r) == b"hello"
    # second call must return the same bytes (iterator already consumed+cached)
    assert _normalize_request_body(r) == b"hello"
    assert r.body == b"hello"


def test_normalize_request_body_handles_bytes_iterator_of_ints():
    # iter(b"hello") yields ints; vcr.Request stores _body as [104, 101, ...].
    # read_body rebuilds via bytes(list_of_ints); _body_to_bytes would not.
    r = _req(iter(b"hello"))
    assert _normalize_request_body(r) == b"hello"
    assert _normalize_request_body(r) == b"hello"
    assert r.body == b"hello"


def test_normalize_request_body_passthrough_none_and_bytes():
    assert _normalize_request_body(_req(None)) is None
    assert _normalize_request_body(_req(b"x")) == b"x"
    # vcr.Request encodes a str body to bytes on assignment, so a "x" body is
    # surfaced (and passed through) as b"x".
    assert _normalize_request_body(_req("x")) == b"x"


# --- urllib3 1.x->2.x chunked-framing normalization (vcrpy #734 / PR #739) ---
#
# urllib3 1.x baked HTTP chunked-transfer framing into the recorded bulk-API
# batch body (e.g. ``25\r\n"FirstName",...\r\n\r\n0\r\n\r\n``); urllib3 2.x sends
# the same logical CSV *unframed*. The matcher must canonicalize both sides so
# the existing, proven cassettes keep replaying without re-recording.

# 0x25 == 37 == len(b'"FirstName","LastName","Email","Id"\r\n')
_UNFRAMED_CSV = b'"FirstName","LastName","Email","Id"\r\n'
_FRAMED_CSV = b'25\r\n"FirstName","LastName","Email","Id"\r\n\r\n0\r\n\r\n'


def test_salesforce_matcher_dechunks_framed_taped_vs_unframed_live():
    # r1 = live request under urllib3 2.x (unframed); r2 = taped cassette body
    # recorded under urllib3 1.x (chunk-framed).
    r1 = _req(_UNFRAMED_CSV)
    r2 = _req(_FRAMED_CSV)
    assert salesforce_matcher(r1, r2) is True


def test_salesforce_matcher_dechunks_symmetrically():
    # Order must not matter: framed-vs-unframed and unframed-vs-framed both match.
    assert salesforce_matcher(_req(_FRAMED_CSV), _req(_UNFRAMED_CSV)) is True


def test_salesforce_matcher_dechunks_iterator_framed_body():
    # urllib3 2.x can also hand the (framed) body over as a bytes iterator.
    r1 = _req(iter(_FRAMED_CSV))
    r2 = _req(_UNFRAMED_CSV)
    assert salesforce_matcher(r1, r2) is True


def test_salesforce_matcher_passes_through_non_chunked_xml():
    # A normal XML body must never be mangled by the de-chunk pass: it does not
    # start with hex+CRLF, so it canonicalizes to itself and still matches.
    xml = (
        b'<jobInfo xmlns="http://www.force.com/2009/06/asyncapi/dataload">'
        b"<operation>upsert</operation></jobInfo>"
    )
    assert salesforce_matcher(_req(xml), _req(xml)) is True


def test_salesforce_matcher_still_detects_real_body_mismatch():
    # De-chunk normalization must not make genuinely different bodies match.
    with pytest.raises(AssertionError):
        salesforce_matcher(_req(b'{"a": 1}'), _req(b'{"a": 2}'))


# --- sf_before_record_request iterator handling (urllib3 2.x) ---------------
#
# VCR applies the request filter to the *live* request on every match attempt.
# urllib3 2.x can present the bulk-upload body as a bytes iterator, which
# vcr.Request stores as a list of ints and re-wraps as a fresh iterator on every
# ``.body`` access. The filter must materialize that to bytes once (clearing
# ``_was_iter``) so repeated passes stay correct and idempotent; otherwise the
# body is progressively corrupted and the proven cassettes fail to replay.


def test_sf_before_record_request_materializes_iterator_body():
    r = _req(iter(b'{"id": "00D000000000000AAA"}'))
    out = sf_before_record_request(_VcrState(), r)
    assert b"00D0xORGID00000000" in out.body
    # _was_iter must be cleared: .body returns plain bytes, not a fresh iterator.
    assert isinstance(out.body, bytes)
    assert out.body == r.body


def test_sf_before_record_request_is_idempotent_for_iterator_body():
    r = _req(iter(b'{"id": "00D000000000000AAA"}'))
    state = _VcrState()
    first = sf_before_record_request(state, r).body
    second = sf_before_record_request(state, r).body
    third = sf_before_record_request(state, r).body
    assert first == second == third
    assert b"00D0xORGID00000000" in third
