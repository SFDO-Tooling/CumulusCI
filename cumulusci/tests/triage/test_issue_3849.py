"""Repro for SFDO-Tooling/CumulusCI#3849.

Pip-installing CumulusCI today picks ``urllib3>=2`` because ``requests``
declares ``urllib3<3,>=1.26`` and CumulusCI itself imposes no upper bound.
Selenium 3.141.0 (locked in by ``selenium<4``) and
``robotframework-seleniumlibrary<6`` rely on the urllib3<2 Timeout API, so
Robot tests fail at runtime with::

    ValueError: Timeout value connect was <object object at 0x...>,
    but it must be an int, float or None.

The modernization (either dropping the ``selenium<4`` /
``robotframework-seleniumlibrary<6`` pins or adding ``urllib3<2`` to the
project dependencies) has not landed on ``origin/dev``.

This test asserts the EXPECTED-modern state. Once any of those
constraints is fixed in ``pyproject.toml`` the assertion will pass and
``strict=False`` lets the existing suite keep going.

See ``docs/triage/v5/repro-results.md``.
"""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import cumulusci
import pytest


def _project_dependencies() -> list[str]:
    # Locate the worktree's pyproject.toml via the installed cumulusci
    # package source so this test is independent of pytest cwd / rootdir.
    pkg_dir = Path(cumulusci.__file__).resolve().parent
    pyproject = pkg_dir.parent / "pyproject.toml"
    assert pyproject.is_file(), f"pyproject.toml not found at {pyproject}"
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    return list(data["project"]["dependencies"])


def _has_urllib3_upper_bound(deps: list[str]) -> bool:
    for spec in deps:
        if re.match(r"^\s*urllib3\b", spec) and "<" in spec:
            return True
    return False


def _has_selenium_pin(deps: list[str], pkg: str) -> bool:
    for spec in deps:
        if re.match(rf"^\s*{re.escape(pkg)}\b.*<", spec):
            return True
    return False


@pytest.mark.xfail(
    reason=("repro for #3849 - see docs/triage/v5/repro-results.md"),
    strict=False,
)
def test_urllib3_or_selenium_modernized():
    """Either pin urllib3<2 explicitly or drop the selenium<4 / "
    robotframework-seleniumlibrary<6 pins."""

    deps = _project_dependencies()

    fixed = _has_urllib3_upper_bound(deps) or not (
        _has_selenium_pin(deps, "selenium")
        and _has_selenium_pin(deps, "robotframework-seleniumlibrary")
    )

    assert fixed, (
        "Issue #3849 still reproduces: pyproject.toml lacks an explicit "
        "urllib3 upper bound while still pinning selenium<4 and "
        "robotframework-seleniumlibrary<6, so pip installs urllib3>=2 "
        "and Robot tests crash on import.\n"
        f"Current dependencies: {deps!r}"
    )
