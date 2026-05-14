# Fix sketch — #3137: cci task run update_package_xml and Salesforce Case Custom Object

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3137>

## Bug

-   `cumulusci/tasks/metadata/package.py:451-458` skips standard objects. - `cumulusci/tasks/metadata/package.py:562-584` `UpdatePackageXml.task_options` has only `path`, `output`, `package_name`, `managed`, `delete`,

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: keep-open — a real product gap remains; mark for design discussion.
-   pass2 labels: `severity:low,area:metadata-etl,type:enhancement,state:needs-design`

---

<!-- subagent 7 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3137.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3137:`).
