"""Regression marker for SFDO-Tooling/CumulusCI#3955.

`SalesforcePlaywright.open_test_browser` splits the ``size`` argument with
``str.split("x", 1)`` and forwards the resulting string fragments straight to
``browser.new_context(viewport={"width": <str>, "height": <str>})``.

Playwright requires ``viewport.width`` / ``viewport.height`` to be ``int``;
passing strings raises::

    browser.newContext: viewport.width: expected integer, got string

Expected behaviour: ``width`` and ``height`` should be cast to ``int`` before
being forwarded.
"""

import sys
import types
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _stub_browser_library():
    """``robotframework-browser`` is not a unit-test dependency, so stub the
    minimum surface that ``SalesforcePlaywright`` imports at module load."""
    browser_mod = types.ModuleType("Browser")
    browser_mod.SupportedBrowsers = mock.MagicMock(name="SupportedBrowsers")
    utils_mod = types.ModuleType("Browser.utils")
    data_types_mod = types.ModuleType("Browser.utils.data_types")
    data_types_mod.KeyAction = mock.MagicMock(name="KeyAction")
    data_types_mod.PageLoadStates = mock.MagicMock(name="PageLoadStates")

    added = []
    for name, mod in (
        ("Browser", browser_mod),
        ("Browser.utils", utils_mod),
        ("Browser.utils.data_types", data_types_mod),
    ):
        if name not in sys.modules:
            sys.modules[name] = mod
            added.append(name)
    try:
        yield
    finally:
        for name in added:
            sys.modules.pop(name, None)



def test_open_test_browser_passes_int_viewport_to_playwright():
    from cumulusci.robotframework.SalesforcePlaywright import SalesforcePlaywright

    lib = SalesforcePlaywright()

    lib._browser = mock.MagicMock(name="Browser")
    lib._browser.new_browser.return_value = "browser-id"
    lib._browser.new_context.return_value = "context-id"
    lib._browser.new_page.return_value = {"page_id": "page-id"}

    lib._cumulusci = mock.MagicMock(name="CumulusCI")
    lib._cumulusci.login_url.return_value = "https://test.example.com"

    def _get_variable_value(name, default=None):
        if name == "${DEFAULT BROWSER SIZE}":
            return "1280x1024"
        if name == "${BROWSER}":
            return "chrome"
        return default

    builtin = mock.MagicMock(name="BuiltIn")
    builtin.get_variable_value.side_effect = _get_variable_value
    builtin.convert_to_boolean.side_effect = lambda v: bool(v)
    lib._builtin = builtin

    with mock.patch.object(lib, "wait_until_salesforce_is_ready"):
        lib.open_test_browser()

    assert lib._browser.new_context.called, "new_context should be invoked"
    _args, kwargs = lib._browser.new_context.call_args
    viewport = kwargs["viewport"]
    assert isinstance(viewport["width"], int), (
        "viewport.width should be int (Playwright contract); got "
        f"{type(viewport['width']).__name__}: {viewport['width']!r}"
    )
    assert isinstance(viewport["height"], int), (
        "viewport.height should be int (Playwright contract); got "
        f"{type(viewport['height']).__name__}: {viewport['height']!r}"
    )
