"""Regression repro for #3353.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-v4.10.0 (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: `Snowfakery._validate_options` in
cumulusci/tasks/bulkdata/snowfakery.py validates the `recipe`
option via `Path(recipe).exists()` only. There is no
`SOURCE_NAME:path` parsing, and no call to
`project_config.sources` / `project_config.get_source(...)`
anywhere in `snowfakery.py`. The 2022 ask (resurfaced 2024-08
by davidjray/jnesong) is to let `recipe:` refer to a recipe in
another configured source repo.

This test asserts that the snowfakery module source mentions
source-resolution machinery (e.g. `project_config.sources`,
`get_source`, or detection of a `SOURCE_NAME:` prefix). On dev
nothing of the sort exists -> XFAIL.
"""

import inspect

import pytest

from cumulusci.tasks.bulkdata import snowfakery as snowfakery_mod


@pytest.mark.xfail(
    reason="repro for #3353 - see docs/triage/v5/repro-results.md",
    strict=False,
)
def test_issue_3353():
    src = inspect.getsource(snowfakery_mod)
    has_source_resolution = any(
        token in src
        for token in (
            "project_config.sources",
            "project_config.get_source",
            "get_source(",
            "SOURCE_NAME",
            'split(":"',
        )
    )
    assert has_source_resolution, (
        "snowfakery.py never resolves SOURCE_NAME:path against "
        "project_config.sources; cross-repo recipes still fail "
        "Path(recipe).exists() (see #3353)."
    )
