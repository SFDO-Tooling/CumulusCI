# Fix sketch - #3758: Flow `push_upgrade_org` is incorrectly defined **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3758> ## Bug - `cumulusci/cumulusci.yml:1161-1177` - final step is `flow: config_qa`. The bug report (correctly, in my view) argues this should be `config_managed` because push upgrades target managed-package orgs (UAT sandboxes), not QA scratch orgs. - Repro test FAILS with `config_qa` != `config_managed`. - Both flows currently expand to the same steps (`deploy_post`, `update_admin_profile`, `load_samp... ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open`- single-line YAML fix; great`good-first-issue` candidate. Out of scope for this triage pass per task constraints (do not fix bugs).

-   | pass2 labels: `severity:medium,area:packaging,area:flows,good-first-issue` --- ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | --------------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                                 | _TBD by fix-PR author_ |
    | Risk                                                                                          | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                                          | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                                          | _TBD_                  |
    | Breaks public CLI surface                                                                     | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3758.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3758:`). |
