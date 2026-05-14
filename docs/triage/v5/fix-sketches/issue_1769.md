# Fix sketch — #1769: Unusual case in test_load

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)
**Theme**: `bulkdata`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/1769>

## Bug

The original line 352 in `158a2d4356f` (May 2020) was: In v4.10.0 the same pattern survives, just wrapped in `MappingLookup`: The pattern repeats at lines 754, 773, 801, 1119, 1187, 1255 — declaring `Id` as a "lookup" key inside the `lookups` dict so `_expand_mapping` can express the after-step's UPDATE-on-Id dependency. davidmreed acknowledged in 2020 it was "a horrible hack" he intended to clean...

## Target

`cumulusci/tasks/bulkdata/tests/test_load.py` lines 736-739

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` — pure test-fixture nit; never escalated to a real bug; original commenters have moved on.
-   pass2 labels: `test-cleanup, low-priority`

---

<!-- subagent 9 -->

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_1769.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #1769:`).
