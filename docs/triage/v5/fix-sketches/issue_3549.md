# Fix sketch - #3549: Deploy to Salesforce does not create a test output

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3549>

## Bug

-   `cumulusci/tasks/salesforce/Deploy.py:49-94` - exposes `test_level` and `specified_tests` options and validates them. - `cumulusci/tasks/salesforce/Deploy.py:150-154` - passes them through to the metadata API call but never captures `runTestResult`/`runTestsResult` from the response. - `rg "junit_output|test_results"` against `cumulusci/tasks/salesforce/Deploy.py` and `cumulusci/salesforce...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - natural feature; tracks #3564.

-   pass2 labels: `enhancement, area:metadata-deploy`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3549.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3549:`).
