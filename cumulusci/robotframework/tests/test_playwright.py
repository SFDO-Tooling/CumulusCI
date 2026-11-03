from unittest import mock

from cumulusci.robotframework.SalesforcePlaywright import SalesforcePlaywright


def _open_test_browser(sfp, **kwargs):
    with (
        mock.patch.object(
            SalesforcePlaywright, "builtin", new_callable=mock.PropertyMock
        ) as mock_builtin,
        mock.patch.object(
            SalesforcePlaywright, "cumulusci", new_callable=mock.PropertyMock
        ) as mock_cci,
    ):
        mock_builtin.return_value.convert_to_boolean.side_effect = lambda value: value
        mock_builtin.return_value.get_variable_value.side_effect = (
            lambda name, default: default
        )
        mock_cci.return_value.login_url.return_value = (
            "https://example.my.salesforce.com"
        )
        sfp.open_test_browser(**kwargs)


def _make_library():
    sfp = SalesforcePlaywright()
    sfp._browser = mock.Mock()
    return sfp


def test_open_test_browser_explicit_size_uses_integer_viewport_dimensions():
    sfp = _make_library()
    _open_test_browser(sfp, size="1920x1080", wait=False)
    viewport = sfp._browser.new_context.call_args[1]["viewport"]
    assert isinstance(viewport["width"], int)
    assert isinstance(viewport["height"], int)
    assert viewport == {"width": 1920, "height": 1080}


def test_open_test_browser_default_size_uses_integer_viewport_dimensions():
    sfp = _make_library()
    _open_test_browser(sfp, wait=False)
    viewport = sfp._browser.new_context.call_args[1]["viewport"]
    assert isinstance(viewport["width"], int)
    assert isinstance(viewport["height"], int)
    assert viewport == {"width": 1280, "height": 1024}
