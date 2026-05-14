# Fix sketch — #2013: Mapping files with steps that are not 1-1 with SObjects are unreliable for extraction

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `bulkdata`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2013>

## Bug

`create_table_if_needed` (`utils.py:133-139`) tries to detect duplicate tables but the SQLAlchemy `Table()` constructor raises first: Reproduction (`/tmp/repro/9/tests/test_2013_multistep.py`) yields the exact 2020 traceback:

## Target

`cumulusci/tasks/bulkdata/utils.py` lines 133-139

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — bug is real, easy to reproduce, easy to fix (catch the SQLAlchemy error and re-raise as `BulkDataException`, or validate at mapping-parse time).
-   pass2 labels: `bug, bulkdata, extract_dataset, error-handling`

---

<!-- subagent 9 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_2013.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2013:`).
