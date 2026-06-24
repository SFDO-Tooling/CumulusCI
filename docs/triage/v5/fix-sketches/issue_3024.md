# Fix sketch - #3024: Order of flow groups in `cumulusci/cumulusci.yml`

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3024>

## Bug

Sequence of unique `group:` values in `cumulusci/cumulusci.yml` (first appearance): `Continuous Integration` is buried near the bottom; `Org Setup` (the user's preferred name) does not exist (uses `Setup`); ordering does not match the user's request.

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `closed:stale-24mo` - 4yr cosmetic VS Code extension request; the true fix is sorting at the consumer (the extension) rather than rearranging the canonical YAML.

-   pass2 labels: `enhancement,stale`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3024.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3024:`).
