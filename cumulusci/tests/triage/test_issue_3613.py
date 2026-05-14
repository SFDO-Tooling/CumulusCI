"""Regression repro for #3613.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `MetadataSingleEntityTransformTask._transform` in
cumulusci/tasks/metadata_etl/base.py:330-332 raises
``CumulusCIException(f"Cannot find metadata file {path}")``
whenever the user-supplied `api_name` does not exactly match
the Metadata API on-disk filename. For Page Layouts the
filename convention is `<Object>-<LayoutName>.layout`; a user
passing just `Account` (the api_name they see in Setup → Object
Manager) crashes with that bare error and no hint about the
expected format or what was actually retrieved.

The proposed UX fix is to drive `_transform` against a fake
retrieve directory and assert the raised exception message
includes either the retrieved filename list or a hint at the
expected `<Object>-<LayoutName>` format.
"""

import pytest

from cumulusci.core.exceptions import CumulusCIException
from cumulusci.tasks.metadata_etl.layouts import AddFieldsToPageLayout


@pytest.mark.xfail(
    reason="repro for #3613 — see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3613(tmp_path):
    retrieve_dir = tmp_path / "retrieve"
    layouts_dir = retrieve_dir / "layouts"
    layouts_dir.mkdir(parents=True)
    # Simulate a successful retrieve with the *correct* MDAPI filename.
    (layouts_dir / "Account-Account Layout.layout").write_text(
        "<Layout xmlns='http://soap.sforce.com/2006/04/metadata'/>"
    )

    task = AddFieldsToPageLayout.__new__(AddFieldsToPageLayout)
    task.retrieve_dir = retrieve_dir
    task.deploy_dir = tmp_path / "deploy"
    task.deploy_dir.mkdir()
    # User typed just the object api_name, like in the bug report.
    task.api_names = {"Account"}
    task.api_version = "59.0"

    with pytest.raises(CumulusCIException) as excinfo:
        task._transform()

    msg = str(excinfo.value)
    helpful = (
        "Account-Account Layout" in msg
        or "<Object>" in msg
        or "available" in msg.lower()
        or "expected format" in msg.lower()
    )
    assert helpful, (
        "MetadataSingleEntityTransformTask still raises a bare "
        f"'Cannot find metadata file ...' message: {msg!r}. "
        "It should reference the retrieved files or the expected "
        "api_name format (see #3613)."
    )
