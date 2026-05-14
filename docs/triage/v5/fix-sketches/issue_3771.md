# Fix sketch - #3771: find_replace transforms on XPath with predicates does not work **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3771> ## Bug - `cumulusci/core/source_transforms/transforms.py:420-435` - naive predicate handling. - `git log --all --oneline --grep="3772\|3771\|XPath.*predicate"` shows ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: keep-open - the leboff PR is a viable starting point; or implement the reporter's "strip xmlns then re-add" approach for simplicity.

-   | pass2 labels: `severity:medium,area:source-transforms,type:bug,has-pr` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ----------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                             | _TBD by fix-PR author_ |
    | Risk                                                                                      | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                                      | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                                      | _TBD_                  |
    | Breaks public CLI surface                                                                 | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3771.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3771:`). |
