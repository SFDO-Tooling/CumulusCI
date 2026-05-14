# Fix sketch - #2507: Undo mode for CumulusCI Insert **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2507> ## Bug No `undo_insert` task exists (`rg -l undo_insert` returns nothing). Closest functionality is `enable_rollback` on `load_dataset` and `snowfakery` tasks: That only triggers rollback on error during the load; it does not provide the post-hoc "delete everything we ever inserted" capability the requester described. ## Target `cumulusci/tasks/bulkdata/load.py` lines 97-99 ## Recommended approach (from triage narrative) - pass1: `closed:stale-24mo` - 4yr feature with partial mitigation already shipped.

-   | pass2 labels: `enhancement,stale,partially-fixed` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | -------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                        | _TBD by fix-PR author_ |
    | Risk                                                                 | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                 | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                 | _TBD_                  |
    | Breaks public CLI surface                                            | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_2507.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #2507:`). |
