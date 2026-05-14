# Fix sketch — #3307: Project Template Support for `cci project init`

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3307>

## Bug

`rg "template" cumulusci/cli/project.py` only finds references to internal Jinja templates rendered from `cumulusci/files/templates/project` (lines 220-329). No `--template` CLI option exists. `project_init` (line 41) takes no template-source argument.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — 4yr; explicitly described by the requester as "low priority / nice to have".
-   pass2 labels: `enhancement,stale`

---

<!-- subagent 2 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3307.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3307:`).
