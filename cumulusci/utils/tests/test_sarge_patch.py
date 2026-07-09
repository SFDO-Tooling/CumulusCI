"""Regression test for SFDO-Tooling/CumulusCI#3852.

``sarge==0.1.7.post1`` (the version pinned via ``pyproject.toml``) ships a
``sarge.Capture`` class with no ``flush()`` method. On Python 3.13+ the
interpreter-shutdown logging path calls ``.flush()`` on the captured stream
objects CumulusCI hands to logging handlers, which surfaces a cosmetic
``AttributeError: 'Capture' object has no attribute 'flush'`` after
``refresh_oauth_token`` runs.

The upstream sarge fix (``def flush(self): pass``) is unreleased, so
``cumulusci.utils`` installs a defensive shim at import time. This test
guards that shim.
"""

import sarge

import cumulusci.utils  # noqa: F401 -- importing applies the Capture.flush shim


def test_sarge_capture_has_flush_after_importing_cumulusci_utils():
    assert hasattr(sarge.Capture, "flush"), (
        "sarge.Capture is missing flush(); CumulusCI must patch it to avoid "
        "AttributeError during interpreter-shutdown logging on Python 3.13+ "
        "(see SFDO-Tooling/CumulusCI#3852)."
    )
    assert callable(sarge.Capture.flush)


def test_sarge_capture_instance_flush_is_a_no_op():
    capture = sarge.Capture()
    try:
        assert capture.flush() is None
    finally:
        capture.close()
