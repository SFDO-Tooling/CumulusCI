"""Regression repro for #3701.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/bulkdata/mapping_parser.py special-cases
the literal field name "Id" throughout (L171, L190, L228, L241,
L422); the field "Id" is always interpreted as the Salesforce 18-char
Id and is bound to the SQLite `sf_id` column. The MappingStep model
has no `primary_key` / `id_field` option to designate a different
field (e.g. an external-id like `BCM_Unique_Id__c`) as the row's
primary key. The user's example yaml `Id : BCM_Unique_Id__c` is
currently interpreted as "extract the SF Id into a column named
BCM_Unique_Id__c", not "use BCM_Unique_Id__c as the primary key".

A real fix introduces a per-step opt-in to override the primary-key
identity, touching extract / load / lookup-resolution.

This test asserts that `MappingStep` exposes some PK-override
affordance. On dev no such field exists, so the assertion fails ->
XFAIL.
"""

import pytest

from cumulusci.tasks.bulkdata.mapping_parser import MappingStep


@pytest.mark.xfail(
    reason="repro for #3701 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3701():
    candidate_attrs = ("primary_key", "id_field", "external_id", "pk_field")
    fields = set(MappingStep.model_fields.keys())
    found = [a for a in candidate_attrs if a in fields]
    assert found, (
        "Expected MappingStep to expose a PK-override field (one of "
        f"{candidate_attrs!r}) so users can designate an external id as the "
        f"row's primary key; existing fields: {sorted(fields)!r}."
    )
