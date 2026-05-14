# Fix sketch — #3931: Specifying a profile in cumulusci.tasks.salesforce.ProfileGrantAllAccess results in an error

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3931>

## Bug

Specifying a profile in cumulusci.tasks.salesforce.ProfileGrantAllAccess results in an error

## Target

`cumulusci/tasks/salesforce/update_profile.py` lines 290-292

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — small, contained fix.
-   pass2 labels: `bug`

**Notes**: Minimal fix at update_profile.py:290-293 — bind `rt_elem = elem.find("recordType")` and check `if rt_elem is not None and rt_elem.text == rt["record_type"]`. Worth a quick scan of sibling code in `_set_record_types` for similar None-deref patterns on optional XML children.

---

<!-- subagent 10 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3931.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3931:`).
