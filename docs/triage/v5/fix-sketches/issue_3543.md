# Fix sketch - #3543: New Option `load_sfdx_project_paths` for dx_convert_from Task **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3543> ## Bug - `cumulusci/tasks/dx_convert_from.py:7-14` exposes only `extra` and `src_dir`; no `load_sfdx_project_paths` / `resolve_sfdx_package_dirs`. - The grep hits in `project_config.py` and `cli/project.py` are unrelated ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: keep-open - feature still unimplemented; reporter offered a draft PR.

-   | pass2 labels: `severity:low,area:metadata-etl,type:enhancement` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ---------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                      | _TBD by fix-PR author_ |
    | Risk                                                                               | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                               | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                               | _TBD_                  |
    | Breaks public CLI surface                                                          | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3543.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3543:`). |
