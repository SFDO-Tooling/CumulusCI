"""Regression repro for #3734.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `PackageUpload._validate_versions` in
cumulusci/tasks/salesforce/package_upload.py runs a SOQL
``ORDER BY MajorVersion DESC, MinorVersion DESC,
PatchVersion DESC, ReleaseState DESC LIMIT 1`` then, when the
returned `ReleaseState` is `Beta`, sets `minor_version` to that
row's `MinorVersion`. When a customer has the typical pattern
(Released 6.13 followed by Beta patch 6.13.1), the query
returns the Beta patch and the next upload is built with
`minor_version=13` — identical to the already-Released minor.
The PackageUploadRequest is rejected with
``FIELD_INTEGRITY_EXCEPTION: The version number must be greater
than the last Managed - Released version number: 6.13``.

This test drives `_validate_versions` against a mocked
`_get_one_record` returning the Beta-patch row and asserts that
the resulting `minor_version` is bumped past the latest Released
minor. On dev it stays at 13 -> XFAIL.
"""

from unittest import mock

import pytest

from cumulusci.tasks.salesforce.package_upload import PackageUpload


@pytest.mark.xfail(
    reason="repro for #3734 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3734():
    task = PackageUpload.__new__(PackageUpload)
    # _validate_versions only consults self.options, self._get_one_record
    task.options = {}
    task._get_one_record = mock.Mock(
        return_value={
            "MajorVersion": 6,
            "MinorVersion": 13,
            "PatchVersion": 1,
            "ReleaseState": "Beta",
        }
    )

    task._validate_versions()

    minor = int(task.options["minor_version"])
    assert minor > 13, (
        "PackageUpload._validate_versions still picks the Beta patch as "
        "'latest' and reuses its MinorVersion; resulting minor_version="
        f"{minor!r} collides with the already-Released 6.13 (see #3734)."
    )
