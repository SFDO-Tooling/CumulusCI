from vcr.request import Request

from cumulusci.tests.pytest_plugins.pytest_sf_vcr import (
    _body_to_bytes,
    _normalize_request_body,
    salesforce_matcher,
    simplify_body,
)


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
