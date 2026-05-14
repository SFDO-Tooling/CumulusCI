"""Regression repro for #3931.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/salesforce/update_profile.py:290-292
contains:

    for elem in tree.findall("layoutAssignments"):
        if elem.find("recordType").text == rt["record_type"]:
            elem.layout.text = layout_option

`elem.find("recordType")` returns `None` whenever a
`<layoutAssignments>` element has no `<recordType>` child (a valid
metadata shape — layoutAssignments without recordType apply to
records lacking a record-type binding). The subsequent `.text`
access then raises `AttributeError: 'NoneType' object has no
attribute 'text'`, which is exactly the user's reported error.

The fix is to bind `rt_elem = elem.find("recordType")` and check
`if rt_elem is not None and rt_elem.text == rt["record_type"]:`
before mutating.

This test parses a profile containing a layoutAssignments element
with no recordType child via the CCI metadata_tree wrapper (the same
type ProfileGrantAllAccess._set_record_types operates on), then
calls `_set_record_types`. On dev the path raises AttributeError so
the assertion fails -> XFAIL.
"""

from unittest import mock

import pytest

from cumulusci.tasks.salesforce.update_profile import ProfileGrantAllAccess
from cumulusci.utils.xml import metadata_tree


@pytest.mark.xfail(
    reason="repro for #3931 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3931():
    profile_xml = b"""<?xml version="1.0" encoding="UTF-8"?>
<Profile xmlns="http://soap.sforce.com/2006/04/metadata">
    <layoutAssignments>
        <layout>Account-Account Layout</layout>
    </layoutAssignments>
    <layoutAssignments>
        <layout>Account-Business Layout</layout>
        <recordType>Account.Business_Account</recordType>
    </layoutAssignments>
    <recordTypeVisibilities>
        <default>false</default>
        <recordType>Account.Business_Account</recordType>
        <visible>true</visible>
    </recordTypeVisibilities>
</Profile>"""
    tree = metadata_tree.fromstring(profile_xml)

    task = ProfileGrantAllAccess.__new__(ProfileGrantAllAccess)
    task.options = {
        "record_types": [
            {
                "record_type": "Account.Business_Account",
                "page_layout": "Account-Replacement Layout",
            }
        ]
    }
    task.namespace_prefixes = {"namespaced_org": "", "managed": ""}
    task.logger = mock.MagicMock()

    raised = None
    try:
        task._set_record_types(tree, "Admin")
    except AttributeError as e:
        raised = e

    assert raised is None, (
        "update_profile._set_record_types raised AttributeError on a "
        f"layoutAssignments without recordType child: {raised}"
    )
