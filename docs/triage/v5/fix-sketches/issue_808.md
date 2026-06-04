# Fix sketch - #808: deploy_packaging flow runs uninstall_packaged_incremental with wrong package name

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `metadata-etl`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/808>

## Bug

-   `UninstallPackaged._init_options` (UninstallPackaged.py:22-25): - Compare to `InstallPackageVersion._init_options` (install_package_version.py:75-79) which DOES use the fall-back chain `name_managed -> name -> namespace`. The asymmetry is the bug. - Bug pattern is unchanged since 2018; no fix has landed.

## Target

`cumulusci/tasks/salesforce/UninstallPackaged.py` lines 22-25

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - small, contained fix.

-   pass2 labels: `bug`, `good-first-issue` **Notes**: jlantz's 2018 follow-up about deprecating `project__package__name_managed` (legacy NPSP-only feature) is a separate, larger conversation; for this triage the minimal symmetric fix is enough.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_808.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #808:`).
