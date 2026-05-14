# Fix sketch - #3518: Task add_picklist_entries always sets a default value for record types **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3518> ## Bug - `cumulusci/tasks/metadata_etl/picklists.py:177` missing `()` after `.lower`. - `cumulusci/tasks/metadata_etl/picklists.py:214-221` unconditionally sets defaults whenever `default` is truthy. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: keep-open - small targeted fix.

-   | pass2 labels: `severity:high,area:metadata-etl,type:bug` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | --------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                               | _TBD by fix-PR author_ |
    | Risk                                                                        | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                        | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                        | _TBD_                  |
    | Breaks public CLI surface                                                   | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3518.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3518:`). |
