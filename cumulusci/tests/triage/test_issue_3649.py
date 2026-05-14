"""Regression repro for #3649.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci/tasks/bulkdata/update_data.py L184 and L211
both call `get_query_operation` / `get_dml_operation` with
`api_options={}` hardcoded empty. `BulkApiDmlOperation` in
`step.py` honors `api_options["bulk_mode"]` for Serial/Parallel
selection, but `UpdateData` never exposes a `bulk_mode` (or
`api_options`) task option, so the Snowfakery-driven update path
cannot run in serial mode. `LoadData` and the snowfakery channel
runner DO let users pick `bulk_mode`; `update_data` is the gap.

A real fix is small (~10 lines): add `bulk_mode` (or `api_options`)
to `UpdateData.task_options` and pipe it into both call sites.

This test asserts that `UpdateData.task_options` exposes a
`bulk_mode` (or `api_options`) option. On dev neither exists, so the
assertion fails -> XFAIL.
"""

import pytest

from cumulusci.tasks.bulkdata.update_data import UpdateData


@pytest.mark.xfail(
    reason="repro for #3649 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3649():
    options = set(UpdateData.task_options.keys())
    assert "bulk_mode" in options or "api_options" in options, (
        "Expected UpdateData.task_options to expose `bulk_mode` (or "
        "`api_options`) so Snowfakery-driven updates can be run in Serial "
        f"mode; current options: {sorted(options)!r}."
    )
