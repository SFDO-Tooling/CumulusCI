# Fix sketch - #3585: Error Occurs when Using `update_package_xml` on object with `xsi:nil="true"` **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3585> ## Bug - `cumulusci/tasks/metadata/package.py:115-130` - when a folder has objects it instantiates the registered parser; for `objects/` the parser uses the metadata tree which is strict about namespaces. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: keep-open - needs either a namespace-shim before parsing or pre-stripping of `xsi:nil` attributes.

-   | pass2 labels: `severity:medium,area:metadata-etl,type:bug,sfdx-compat` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ----------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                             | _TBD by fix-PR author_ |
    | Risk                                                                                      | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                                      | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                                      | _TBD_                  |
    | Breaks public CLI surface                                                                 | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3585.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3585:`). |
