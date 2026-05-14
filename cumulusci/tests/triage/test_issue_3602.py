"""Regression marker for SFDO-Tooling/CumulusCI#3602.

The ``Open Test Browser`` keyword (both the Selenium ``.robot`` keyword and
the Playwright Python implementation) accepts only ``size``, ``alias`` /
``useralias``, ``wait`` and (Playwright only) ``record_video``.  There is no
way to pass through Chrome / Firefox / Playwright browser options such as
extensions, ``--incognito``, download directory, ``--accept-ssl-errors`` etc.

The reporter asks for a hook to forward browser capabilities / options.  This
test asserts the Playwright implementation surfaces a ``browser_options``
(or ``extra_options``) keyword argument; the test fails today because the
signature has no such hook.
"""

import inspect
import sys
import types
from unittest import mock

import pytest


@pytest.fixture(autouse=True)
def _stub_browser_library():
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


@pytest.mark.xfail(
    reason=("repro for #3602 — see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_open_test_browser_exposes_browser_options_hook():
    """The Playwright ``open_test_browser`` should expose a kwarg that lets
    callers forward browser options/capabilities (extensions, incognito,
    download dir, accept-ssl, etc.).
    """
    from cumulusci.robotframework.SalesforcePlaywright import SalesforcePlaywright

    sig = inspect.signature(SalesforcePlaywright.open_test_browser)
    params = sig.parameters
    accepts_browser_options = (
        "browser_options" in params
        or "extra_options" in params
        or "browser_args" in params
        or "options" in params
        or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
    )
    assert accepts_browser_options, (
        "SalesforcePlaywright.open_test_browser should accept a "
        "browser_options/extra_options keyword (or **kwargs) so callers can "
        "forward Chrome/Firefox/Playwright capabilities (#3602). "
        f"Actual signature: {sig}"
    )
