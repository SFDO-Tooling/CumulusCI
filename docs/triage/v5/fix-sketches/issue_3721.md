# Fix sketch - #3721: `create_package_version` `version_name` default should be version number, not "Release"

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3721>

## Bug

-   `cumulusci/tasks/create_package_version.py:184` - `version_name=self.options.get("version_name") or "Release"`. Default is still the literal string `"Release"`. - `cumulusci/cumulusci.yml:684-686` - `upload_production` hard-codes `name: Release`. - `cumulusci/tasks/salesforce/package_upload.py:147-154` - passes `VersionName` straight through; no jinja2/template support.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - needs upstream port + design (templating? plain version number? both 1GP and 2GP?).

-   pass2 labels: `severity:low,area:packaging,area:1gp,area:2gp`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3721.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3721:`).
