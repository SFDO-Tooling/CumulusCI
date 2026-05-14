# Fix sketch - #3734: upload_production fails with FIELD_INTEGRITY_EXCEPTION when latest is Beta patch **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3734> ## Bug - `cumulusci/tasks/salesforce/package_upload.py:80-98` - SOQL query, `ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, ReleaseState DESC LIMIT 1`. - `cumulusci/tasks/salesforce/package_upload.py:134-137` - Beta branch sets `minor_version` to the same minor. - Test passes on v4.10.0 with mocked `_get_one_record`. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open` - confirmed real bug; remove the stale `cannot-reproduce`/`awaiting-more-details` labels.

-   | pass2 labels: `bug` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | -------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                          | _TBD by fix-PR author_ |
    | Risk                                   | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`   | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`   | _TBD_                  |
    | Breaks public CLI surface              | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3734.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3734:`). |
