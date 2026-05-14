# Fix sketch — #3910: JSON Schema incorrectly defines namespaced field as string instead of boolean for scratch org configuration

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `scratch-org-config`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3910>

## Bug

JSON Schema incorrectly defines namespaced field as string instead of boolean for scratch org configuration

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach: land PR #3911 essentially as-is (one-line Pydantic field change in `cumulusci_yml.py` + `make schema` regenerated `cumulusci.jsonschema.json`). Both edits must ship together because `test_schema_is_current` would otherwise fail.
-   Target file:line: `cumulusci/utils/yaml/cumulusci_yml.py:150` (`namespaced: str = None` → `namespaced: bool = None`); regenerate `cumulusci/schema/cumulusci.jsonschema.json`.
-   Size: small.
-   Risk: low. The only Pydantic consumers of `ScratchOrg.namespaced` are YAML-validation pathways; the runtime keychain path already uses booleans.
-   API break: no (silent coercion was incidental and arguably already broken for users).

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3910.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3910:`).
