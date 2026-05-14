# Fix sketch - #2508: Manual load retries **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `bulkdata`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2508> ## Bug - `cci task list` returns no retry-named task. - `load.py` has an `enable_rollback` option (`:97-98`, `RollbackType` enum at `:1051`) but rollback **undoes successful inserts when failures occur** - the opposite of "retry the failures." - `RowErrorChecker` (`utils.py:158`) only logs and optionally raises; it does not persist a failed-rows artifact that could be replayed. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open` - distinct from rollback; would need (a) failed-row CSV/SQL persistence + (b) a new `retry_failed_load` task that consumes it.

-   | pass2 labels: `enhancement, bulkdata, load_dataset, reliability` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ----------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                       | _TBD by fix-PR author_ |
    | Risk                                                                                | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                                | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                                | _TBD_                  |
    | Breaks public CLI surface                                                           | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_2508.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #2508:`). |
