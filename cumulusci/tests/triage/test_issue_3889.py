"""Regression repro for #3889.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: CumulusCI exposes uninstall tasks only for 1GP managed
packages (via namespace + InstalledPackage destructiveChanges):

  - cumulusci/cumulusci.yml:615-642 — uninstall_managed,
    uninstall_packaged, uninstall_packaged_incremental, uninstall_src,
    uninstall_pre, uninstall_post. None accept a 04t id.
  - cumulusci/tasks/salesforce/UninstallPackage.py — `UninstallPackage`
    only accepts `namespace` and `purge_on_delete`.
  - cumulusci/salesforce_api/package_zip.py — `UninstallPackageZipBuilder`
    writes destructiveChanges referencing InstalledPackage by namespace;
    no 04t code path.

The user wants a task that accepts an `04t...` SubscriberPackageVersion
id (or `Package2Version.Id`) and uninstalls via Tooling API (analogous
to `sf package uninstall -p 04t...`) so it doesn't depend on sf CLI
stability.

A real fix introduces a new task (e.g. `UninstallPackageVersion`)
that calls the Tooling API directly.

This test asserts `UninstallPackage` (or a sibling task) accepts a
SubscriberPackageVersion / 04t id. On dev no such option exists, so
the assertion fails -> XFAIL.
"""

import pytest

from cumulusci.tasks.salesforce.UninstallPackage import UninstallPackage


@pytest.mark.xfail(
    reason="repro for #3889 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3889():
    options = set(UninstallPackage.task_options.keys())
    candidate_options = (
        "version_id",
        "subscriber_package_version_id",
        "package_version_id",
        "package_version",
    )
    found = [opt for opt in candidate_options if opt in options]
    assert found, (
        "Expected UninstallPackage (or a sibling task) to expose a "
        f"04t / SubscriberPackageVersion id option (one of "
        f"{candidate_options!r}) for 2GP uninstalls; current options: "
        f"{sorted(options)!r}."
    )
