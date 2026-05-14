"""Regression repro for #3619.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``GitHubDependencyPin``
(cumulusci/core/dependencies/dependencies.py:79-101) only declares
``github: str`` and ``tag: str``. Adding ``password_env_name:`` to a
``dependency_pins:`` entry triggers
``DependencyParseError: Unable to parse dependency pin: {...}`` from
``parse_dependency_pin()``/``parse_pins()`` because Pydantic rejects
the extra field.

(Part B of #3619 - the silent password drop in ``pin.pin()`` - is
captured at the same location: even if Part A is fixed by adding the
field, ``pin.pin()`` calls ``GitHubTagResolver().resolve(...)``
directly and bypasses the password-propagation block in
``resolvers.py`` ~L644-654. Both parts need a fix.)

The minimal fix for Part A is to add
``password_env_name: Optional[str] = None`` to
``GitHubDependencyPin``; the test here asserts ``parse_pins`` no
longer raises ``DependencyParseError`` on an entry carrying
``password_env_name``.
"""

import pytest

from cumulusci.core.dependencies.dependencies import parse_pins
from cumulusci.core.exceptions import DependencyParseError


@pytest.mark.xfail(
    reason="repro for #3619 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3619():
    pin_dict = {
        "github": "https://github.com/example/repo",
        "tag": "release/1.0",
        "password_env_name": "MY_INSTALL_KEY",
    }

    raised = None
    parsed = None
    try:
        parsed = parse_pins([pin_dict])
    except BaseException as e:
        raised = e

    assert not isinstance(raised, DependencyParseError), (
        "parse_pins still raises DependencyParseError for an entry that includes "
        "password_env_name; GitHubDependencyPin only declares github+tag, so the "
        f"password_env_name field is rejected. Got: {raised!r}"
    )
    assert parsed is not None and len(parsed) == 1
    assert getattr(parsed[0], "password_env_name", None) == "MY_INSTALL_KEY", (
        "Even if the pin parses, password_env_name is not carried onto the pin "
        "object (#3619 Part B). Fix must both accept and propagate it."
    )
