# Fix sketch — #3692: No parser configuration found for subdirectory digitalExperiences

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `metadata-etl`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3692>

## Bug

-   `cumulusci/tasks/metadata/metadata_map.yml` has no `digitalExperiences` key. - `cumulusci/tasks/metadata/package.py:115-118` raises

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: keep-open — add `digitalExperiences` (and likely
    `digitalExperienceConfigs`) entries to `metadata_map.yml` with
    appropriate parser classes (probably a bundle parser).
-   pass2 labels: `severity:medium,area:metadata-etl,type:bug`

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

`cumulusci/tests/triage/test_issue_3692.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3692:`).
