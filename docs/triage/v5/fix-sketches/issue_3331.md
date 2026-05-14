# Fix sketch — #3331: Task update_package_xml does not write correct package.xml for AssignmentRules

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3331>

## Bug

-   `cumulusci/tasks/metadata/metadata_map.yml:45-48` maps the `assignmentRules` folder to `type: AssignmentRule` (singular). MDAPI expects the plural type name (cf. `autoResponseRules:` at lines 60-63

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: keep-open — one-line YAML fix; reporter offered a PR.
-   pass2 labels: `severity:medium,area:metadata-etl,type:bug,good-first-issue`

---

<!-- subagent 6 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3331.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3331:`).
