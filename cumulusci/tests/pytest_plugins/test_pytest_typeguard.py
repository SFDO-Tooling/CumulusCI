"""Pin tests for the pytest_typeguard plugin's Python 3.14 compatibility shim.

typeguard 2.13.3 is pinned in pyproject.toml (TODO: upgrade to v4) and its
import hook references ast.Str, which was removed in Python 3.14. The plugin
must skip installing the hook on Python 3.14+ so pytest's session start does
not crash and take the entire suite down.

These tests use mocks to simulate both Python version regimes so they pass
under any interpreter that has a typeguard package available.
"""

import importlib
import sys
import types
from unittest import mock


def _make_fake_typeguard():
    """Build a fake `typeguard.importhook` module exposing a Mock install_import_hook."""
    fake_install_import_hook = mock.Mock()
    fake_typeguard = types.ModuleType("typeguard")
    fake_importhook = types.ModuleType("typeguard.importhook")
    fake_importhook.install_import_hook = fake_install_import_hook
    fake_typeguard.importhook = fake_importhook
    return fake_typeguard, fake_importhook, fake_install_import_hook


def _reload_plugin():
    from cumulusci.tests.pytest_plugins import pytest_typeguard

    importlib.reload(pytest_typeguard)
    return pytest_typeguard


def test_pytest_sessionstart_is_noop_on_py314():
    """On Python 3.14+, pytest_sessionstart must not call install_import_hook."""
    fake_typeguard, fake_importhook, fake_install_import_hook = _make_fake_typeguard()

    with (
        mock.patch.dict(
            sys.modules,
            {"typeguard": fake_typeguard, "typeguard.importhook": fake_importhook},
        ),
        mock.patch.object(sys, "version_info", (3, 14, 0, "final", 0)),
    ):
        plugin = _reload_plugin()
        result = plugin.pytest_sessionstart(None)

    assert result is None
    fake_install_import_hook.assert_not_called()


def test_pytest_sessionstart_installs_hook_on_py313():
    """On Python <= 3.13, pytest_sessionstart must install the typeguard import hook."""
    fake_typeguard, fake_importhook, fake_install_import_hook = _make_fake_typeguard()

    with (
        mock.patch.dict(
            sys.modules,
            {"typeguard": fake_typeguard, "typeguard.importhook": fake_importhook},
        ),
        mock.patch.object(sys, "version_info", (3, 13, 0, "final", 0)),
    ):
        plugin = _reload_plugin()
        plugin.pytest_sessionstart(None)

    fake_install_import_hook.assert_called_once_with(packages=["cumulusci"])
