"""Regression repro for #3951.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `SetDuplicateRuleStatus` extends
`MetadataSingleEntityTransformTask` whose `_transform` looks for
metadata files by the literal `api_name`. DuplicateRule API
names always follow `<Object>.<RuleName>`; users typing only
the rule name (e.g.
``Standard_Rule_for_Leads_with_Duplicate_Contacts``) crash with
the unhelpful ``Cannot find metadata file ... .duplicateRule``.
The task itself does not document or detect this format
requirement.

Proposed UX fix: improve the `api_names` option help string to
call out the ``<Object>.<RuleName>`` format. This test asserts
that today's task surface includes the format hint. On dev it
doesn't -> XFAIL.

(Same root-cause family as #3613.)
"""

import pytest

from cumulusci.tasks.metadata_etl.duplicate_rules import (
    SetDuplicateRuleStatus,
)


@pytest.mark.xfail(
    reason="repro for #3951 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3951():
    api_names_opt = SetDuplicateRuleStatus.task_options.get("api_names", {})
    description = (api_names_opt.get("description") or "").lower()
    hints_at_object_prefix = (
        "<object>" in description
        or "object_name" in description
        or "object.rulename" in description
        or "object." in description
    )
    assert hints_at_object_prefix, (
        "SetDuplicateRuleStatus.task_options['api_names'] description "
        f"({description!r}) still does not warn the user that "
        "DuplicateRule API names require the <Object>.<RuleName> form "
        "(see #3951)."
    )
