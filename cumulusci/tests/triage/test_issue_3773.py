"""Regression repro for #3773.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (no_reverify_needed).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: ``RetrieveProfileApi._queries_retrieve_permissions``
(cumulusci/salesforce_api/retrieve_profile_api.py:164-195) only builds
queries for ``SetupEntityAccess``, ``ObjectPermissions``,
``PermissionSetTabSetting``, and a flow-specific ``SetupEntityAccess``.
No ``FieldPermissions`` query is built. As a consequence,
``retrieve_profile`` cannot discover that a profile has only
field-level (not object-level) permissions on something like
``AccountContactRelation``, and the parent SObject is never added to
the package.xml - so its field permissions are silently dropped from
the retrieved profile XML.

The fix is to add a ``FieldPermissions`` query against
``Parent.Profile.Name`` and include those parent SObjectTypes in the
``CustomObject`` retrieve set.

This test asserts ``_queries_retrieve_permissions`` source mentions
``FieldPermissions``; on dev it fails because the query is not built.
"""

import inspect

import pytest

from cumulusci.salesforce_api.retrieve_profile_api import RetrieveProfileApi


@pytest.mark.xfail(
    reason="repro for #3773 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3773():
    src = inspect.getsource(RetrieveProfileApi._queries_retrieve_permissions)
    has_field_perms = "FieldPermissions" in src or "fieldpermissions" in src.lower()
    assert has_field_perms, (
        "RetrieveProfileApi._queries_retrieve_permissions still does not query "
        "FieldPermissions; profiles with only field-level perms on an object "
        "(e.g. AccountContactRelation) will be retrieved with those perms missing "
        "(see #3773)"
    )
