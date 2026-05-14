"""Regression repro for #3165.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `ProfileGrantAllAccess._generate_package_xml` in
cumulusci/tasks/salesforce/update_profile.py:137-138 calls
`_expand_package_xml(package_xml)` only when
`include_packaged_objects=True`. `_expand_package_xml_objects`
— the helper that walks `record_types` and adds any referenced
CustomObject to the retrieve package.xml — is invoked only from
inside `_expand_package_xml` (line 182). When a user specifies
`record_types` referencing a standard object (e.g. Case) and
keeps `include_packaged_objects=False`, the retrieve package.xml
omits Case, the deploy then fails because the profile XML
references an unretrievable record type.

The proposed minimal fix is to always invoke
`_expand_package_xml_objects` regardless of
`include_packaged_objects`, since that helper makes no API call.

This test asserts that on dev `_generate_package_xml` (or
`_expand_package_xml_objects`) is wired so that `record_types`
expansion runs even when `include_packaged_objects` is False.
We approximate this by reading the source of
`_generate_package_xml` and asserting it calls
`_expand_package_xml_objects` directly (i.e. not only via the
gated `_expand_package_xml`). On dev that direct call is
missing -> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.salesforce.update_profile import ProfileGrantAllAccess


@pytest.mark.xfail(
    reason="repro for #3165 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3165():
    src = inspect.getsource(ProfileGrantAllAccess._generate_package_xml)
    calls_objects_helper_directly = (
        "_expand_package_xml_objects(" in src
        or "self._expand_package_xml_objects" in src
    )
    assert calls_objects_helper_directly, (
        "_generate_package_xml does not invoke "
        "_expand_package_xml_objects outside the "
        "`include_packaged_objects` branch; record_types pointing at "
        "objects not in admin_profile.xml still get dropped (see #3165)."
    )
