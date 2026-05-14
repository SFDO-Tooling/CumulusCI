# Fix sketch — #3593: `dx` task doesn't work for some commands like `project convert source`

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `packaging`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3593>

## Bug

-   `cumulusci/tasks/sfdx.py:46-51` — `SFDXOrgTask._get_command` unconditionally appends `" -o {username}"` for any `ScratchOrgConfig`, regardless of whether the underlying sf subcommand accepts a target-org flag. - Repro test FAILS with the resulting command: `sf project convert source -r src -d force-app -o test@example.com` — the same shape that the issue reporter said sf cli rejects. - Not...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` — needs an opt-out option (e.g. `pass_org: False` or a `no_org_command` whitelist). Verifying actual sf cli rejection of `-o` for `project convert source` would need an org/sf cli; the CCI side of the bug is unchanged.
-   pass2 labels: `severity:medium,area:packaging,area:sfdx,area:dx-task,state:needs-design`

---

<!-- subagent 3 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3593.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3593:`).
