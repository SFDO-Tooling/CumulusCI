"""Regression repro for #3768.

See docs/triage/v5/repro-results.md for full narrative.
Verdict: REPRODUCED-on-dev (R1+R2 + Task 4 recovery).
This xfail marker will be removed by the corresponding fix-PR.

Root cause: the Snowfakery channel runner creates a separate working
directory per batch via `shutil.copytree(template_path, data_dir)`
(`cumulusci/tasks/bulkdata/snowfakery_utils/queue_manager.py:322`).
Before that copy, `Snowfakery._cleanup_object_tables` (snowfakery.py:
720-729) drops every non-`sf_ids` table from the template. So when
batch 2+ starts, the SQLite database carried in the template only
contains `*_sf_ids` mapping tables, with none of the actual rows
created during the initial `just_once: true` batch.

Snowfakery's `random_reference: Account` resolves at generation time
against rows in the recipe-local database. With just_once Accounts
unavailable after batch 1, subsequent batches generate Contacts with
no Accounts to reference - exactly the user's symptom.

The fix needs to preserve rows of just_once-referenced objects in
the template DB carried to subsequent batches (not just `_sf_ids`
rows).

This test invokes `_cleanup_object_tables` against an engine that
contains a `just_once`-style data table and a corresponding
`account_sf_ids` mapping table, then uses the engine inspector to
check whether the data table physically still exists. On dev the
data table is physically dropped, so the assertion fails -> XFAIL.
"""

from sqlalchemy import Column, MetaData, String, Table, create_engine, inspect

import pytest

from cumulusci.tasks.bulkdata.snowfakery import Snowfakery


@pytest.mark.xfail(
    reason="repro for #3768 - see docs/triage/v5/repro-results.md", strict=False
)
def test_issue_3768():
    engine = create_engine("sqlite:///:memory:")
    metadata = MetaData(bind=engine)
    Table(
        "account",
        metadata,
        Column("id", String(255), primary_key=True),
        Column("Name", String(255)),
    )
    Table(
        "account_sf_ids",
        metadata,
        Column("id", String(255), primary_key=True),
        Column("sf_id", String(255)),
    )
    metadata.create_all(engine)

    assert "account" in inspect(engine).get_table_names(), (
        "test setup is wrong - account table not created"
    )

    task = Snowfakery.__new__(Snowfakery)
    task._cleanup_object_tables(engine, metadata)

    remaining = set(inspect(engine).get_table_names())
    assert "account" in remaining, (
        "Snowfakery._cleanup_object_tables physically drops non-sf_ids tables; "
        "just_once-referenced data is lost when subsequent batches start. "
        f"Remaining physical tables after cleanup: {sorted(remaining)}"
    )
