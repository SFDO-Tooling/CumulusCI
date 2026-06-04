# Fix sketch - #3889: Uninstall 2GP task request

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3889>

## Bug

-   `cumulusci/cumulusci.yml:615-642` - Uninstall tasks: `uninstall_managed`, `uninstall_packaged`, `uninstall_packaged_incremental`, `uninstall_src`, `uninstall_pre`, `uninstall_post`. None take a 04t id. - `cumulusci/tasks/salesforce/UninstallPackage.py:6-32` - `UninstallPackage` accepts only `namespace` (and `purge_on_delete`). Builds an `UninstallPackageZipBuilder` from the namespace. - `c...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open`- needs a new`UninstallPackageVersion`task (or extend`UninstallPackage`) that calls Tooling API directly so it doesn't depend on sf cli stability (per the user's note about sf cli breaking changes).

-   pass2 labels: `severity:medium,area:packaging,area:2gp,area:unlocked-package`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3889.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3889:`).
