"""Regression repro for #3700.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``MappingStep._get_required_permission_types``
(cumulusci/tasks/bulkdata/mapping_parser.py:361-381) unconditionally
returns ``("updateable", "createable")`` for any operation in
``(UPSERT, ETL_UPSERT)``. Master-detail lookup fields in Salesforce are
``createable: True`` but ``updateable: False`` (you cannot reparent a
master-detail child after creation), so
``_check_field_permission`` returns ``False`` for the MD lookup on an
upsert mapping. ``_validate_field_dict`` then errors with
``Field xxx__c does not have the correct permissions ('updateable',
'createable') for this operation`` - exactly the symptom #3700 reports.

The fix is a field-shape-aware permission check: for upsert lookup
fields that look like master-detail (``cascadeDelete: True``,
``updateable: False``, ``createable: True``), accept ``createable``
alone - the MD lookup never gets updated post-insert anyway.

This test simulates ``_check_field_permission`` against an MD-shaped
describe and asserts the call returns ``True`` for an UPSERT operation.
On dev it fails because the permission check still demands
``updateable``.
"""

import pytest

from cumulusci.tasks.bulkdata.mapping_parser import MappingStep
from cumulusci.tasks.bulkdata.step import DataOperationType


@pytest.mark.xfail(
    reason="repro for #3700 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3700():
    step = MappingStep(
        sf_object="Order__c",
        table="Order__c",
        action="upsert",
        update_key="ExternalId__c",
        fields={"Name": "Name", "Account__c": "Account__c"},
    )

    md_describe = {
        "Account__c": {
            "createable": True,
            "updateable": False,
            "name": "Account__c",
        }
    }

    allowed = step._check_field_permission(
        md_describe, "Account__c", DataOperationType.UPSERT
    )
    assert allowed, (
        "MappingStep._check_field_permission still rejects an UPSERT against a "
        "master-detail-shaped (createable=True, updateable=False) lookup field; "
        "upsert should treat the MD lookup as create-only and accept "
        "createable alone (see #3700)"
    )
