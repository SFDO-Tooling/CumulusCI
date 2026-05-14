"""Regression repro for #2013.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: cumulusci.tasks.bulkdata.utils.create_table_if_needed builds
a SQLAlchemy `Table(tablename, metadata, *fields)` before calling
`inspector.has_table()`. When two mapping steps share the same
sf_object name, the SQLAlchemy `Table()` constructor raises
`InvalidRequestError: Table 'X' is already defined ...` BEFORE the
intended `BulkDataException("Table already exists: ...")` is raised.

The fix is to either (a) wrap the `Table()` call in a try/except and
re-raise as BulkDataException, or (b) validate uniqueness at
mapping-parse time. Either way, when the table already exists in the
metadata, callers should observe a CumulusCI-typed BulkDataException,
not a SQLAlchemy-typed InvalidRequestError.
"""

from sqlalchemy import Column, MetaData, String, create_engine

import pytest

from cumulusci.core.exceptions import BulkDataException
from cumulusci.tasks.bulkdata.utils import create_table_if_needed


@pytest.mark.xfail(
    reason="repro for #2013 — see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_2013():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData(bind=engine)

    create_table_if_needed(
        "Account", metadata, [Column("sf_id", String(255), primary_key=True)]
    )

    raised = None
    try:
        create_table_if_needed(
            "Account", metadata, [Column("sf_id", String(255), primary_key=True)]
        )
    except BaseException as e:
        raised = e

    assert isinstance(raised, BulkDataException), (
        "Expected BulkDataException for duplicate table; "
        f"got {type(raised).__name__}: {raised}"
    )
