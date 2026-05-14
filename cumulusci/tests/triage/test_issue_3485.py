"""Regression repro for #3485.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/apex/testrunner.py:802-833 writes a JUnit
`test_results.xml` that:
- has no `<?xml version="1.0" ...?>` declaration
- writes a bare `<testsuite>` element, not the standard `<testsuites>`
  wrapper that JUnit consumers (Jenkins, GitHub Actions, etc.) expect

Per the user's issue body, downstream JUnit parsers reject this
malformed XML. The minimal fix is to emit the XML declaration and the
top-level `<testsuites>` wrapper.

This test invokes `_write_output` directly with mocked results and
asserts the generated content starts with an XML declaration and
contains a `<testsuites>` element. On dev neither is true, so the
assertion fails -> XFAIL.
"""

import pathlib
import tempfile
from unittest import mock

import pytest

from cumulusci.tasks.apex.testrunner import RunApexTests


@pytest.mark.xfail(
    reason="repro for #3485 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3485():
    with tempfile.TemporaryDirectory() as tmpdir:
        junit_path = pathlib.Path(tmpdir) / "test_results.xml"
        task = RunApexTests.__new__(RunApexTests)
        task.options = {"junit_output": str(junit_path), "json_output": ""}
        task.logger = mock.MagicMock()
        test_results = [
            {
                "ClassName": "FooTest",
                "Method": "method_a",
                "Outcome": "Pass",
                "Stats": {"duration": "0.1"},
                "Message": None,
                "StackTrace": None,
            }
        ]
        task._write_output(test_results)
        content = junit_path.read_text(encoding="utf-8")

    assert content.lstrip().startswith("<?xml"), (
        "JUnit output missing <?xml ...?> declaration. "
        f"First 80 chars: {content[:80]!r}"
    )
    assert "<testsuites" in content, (
        f"JUnit output missing required <testsuites> wrapper. Full content:\n{content}"
    )
