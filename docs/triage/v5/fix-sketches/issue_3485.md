# Fix sketch - #3485: "cci task run run_tests" generates incorrect test_results.xml format **Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3485> ## Bug - `cumulusci/tasks/apex/testrunner.py:803-834` - `_write_output` opens `junit_output` and writes `'<testsuite tests="{}">\n'` with no `<?xml version=...?>` declaration and no enclosing `<testsuites>` element. - The closing tag at line 834 is `</testsuite>`. This exactly matches the malformed XML the reporter showed. - `junit_output` defaults to `test_results.xml` (line 201-203), unchanged. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open` - small mechanical fix, still affects users producing JUnit reports for CI.

-   | pass2 labels: `bug, area:apex, good-first-issue` ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | --------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                   | _TBD by fix-PR author_ |
    | Risk                                                            | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                            | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                            | _TBD_                  |
    | Breaks public CLI surface                                       | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3485.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3485:`). |
