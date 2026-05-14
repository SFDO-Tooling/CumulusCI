"""Regression repro for #3953.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``AddPicklistEntries._init_options``
(cumulusci/tasks/metadata_etl/picklists.py around line 68) checks
``all("fullName" in entry for entry in self.options["entries"])``
without first parsing ``entries`` from a JSON string. When the task
is invoked from the CLI, ``-o entries '[{...}]'`` arrives as the
literal string; iterating that string walks characters one at a time,
none contain the substring ``"fullName"``, and the task always errors
with ``Error: The 'fullName' key is required on all picklist values``.

Net effect: ``cci task run add_picklist_entries`` is unusable from the
CLI on v4.10.0.

The minimal fix is to JSON-parse ``self.options["entries"]`` when it
is a string before validating it (and apply the same coercion to
``record_types`` for symmetry). A more general fix is schema-driven
list coercion via the new Pydantic ``Options`` model.

This test asserts the source of ``AddPicklistEntries._init_options``
parses string-form ``entries`` (e.g. references ``json.loads`` or
``process_list_arg`` on ``entries``); on dev it fails because no such
parsing exists.
"""

import inspect

import pytest

from cumulusci.tasks.metadata_etl.picklists import AddPicklistEntries


@pytest.mark.xfail(
    reason="repro for #3953 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3953():
    src = inspect.getsource(AddPicklistEntries._init_options)
    parses_entries = any(
        token in src
        for token in (
            'json.loads(self.options["entries"]',
            "json.loads(self.options['entries']",
            'json.loads(self.options.get("entries"',
            "json.loads(self.options.get('entries'",
            'process_list_arg(self.options["entries"]',
            "process_list_arg(self.options['entries']",
        )
    )
    assert parses_entries, (
        "AddPicklistEntries._init_options still does not parse the 'entries' "
        "option from a JSON string; CLI invocation 'cci task run "
        'add_picklist_entries -o entries "[{...}]"\' iterates the string char '
        "by char and always raises \"'fullName' key is required\" (see #3953)"
    )
