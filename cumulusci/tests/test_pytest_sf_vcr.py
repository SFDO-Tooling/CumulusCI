from cumulusci.tests.pytest_plugins.pytest_sf_vcr import _body_to_bytes, simplify_body


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
