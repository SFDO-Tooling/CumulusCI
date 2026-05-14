# Fix sketch - #3492: Enhance the "-o" option of "cci flow run" to accept "project\_\_custom" attribute values **Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3492> ## Bug - `cumulusci/cli/flow.py:152-162` - parses `-o` pairs by splitting key on `"__"` and unpacking into exactly two parts (`task_name, option_name = key.split("__")`). - A user passing `-o project__custom__myattr value` would actually error with "too many values to unpack" because the split yields three elements; even worded as `-o project__custom value` there is no codepath that writes into `proj... ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open` - legitimate usability gap for matrix-style CI.

-   | pass2 labels: `enhancement, area:cli` ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ---------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                        | _TBD by fix-PR author_ |
    | Risk                                                 | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                 | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                 | _TBD_                  |
    | Breaks public CLI surface                            | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3492.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3492:`). |
