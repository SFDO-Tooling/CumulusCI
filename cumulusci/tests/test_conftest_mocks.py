from unittest import mock

from cumulusci.conftest import MockHttpResponse


def test_mock_http_response_allows_child_attribute_access():
    resp = MockHttpResponse(status=200)
    # Without the _get_child_mock override, accessing an auto-created child
    # attribute raises TypeError (MockHttpResponse.__init__ requires `status`).
    # The override returns a plain Mock instead.
    child = resp.some_undefined_attribute
    assert isinstance(child, mock.Mock)


def test_mock_http_response_emulates_urllib3_response_surface():
    resp = MockHttpResponse(status=200)
    # real mapping (urllib3 retry-after lookup + requests CaseInsensitiveDict)
    assert resp.headers.get("Retry-After") is None
    # iterable, empty body
    assert list(resp.stream(8192, decode_content=True)) == []
    # not a redirect (bare Mock would be truthy)
    assert resp.get_redirect_location() is False
    # falsy -> requests skips cookie extraction
    assert not resp._original_response
