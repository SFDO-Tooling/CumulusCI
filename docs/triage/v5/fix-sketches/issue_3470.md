# Fix sketch - #3470: Rename `ci_master` to `ci_main` (or alias) **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3470> ## Bug `rg "ci_main"` returns no matches. davidmreed's 2022 reply indicated this requires flow-aliasing infrastructure first. ## Target `cumulusci/cumulusci.yml` lines 823-835 ## Recommended approach (from triage narrative) - pass1: `closed:stale-24mo` - 4yr stale; preserve as `closed:stale-24mo` rather than dismiss; the inclusive-language motivation is real and could be revisited if flow aliasing lands.

-   | pass2 labels: `enhancement,stale,inclusive-language` ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                       | _TBD by fix-PR author_ |
    | Risk                                                                | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                | _TBD_                  |
    | Breaks public CLI surface                                           | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3470.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3470:`). |
