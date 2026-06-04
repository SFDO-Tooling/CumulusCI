# Fix sketch - #3953: add_picklist_entries never works through CLI

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3953>

## Bug

add\*picklist_entries never works through CLI

## Target

\_See narrative for target file:line.\*

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - single-line fix.

-   pass2 labels: `bug`, `good-first-issue` **Notes**: Minimal fix in `AddPicklistEntries._init_options`: `if isinstance(self.options.get("entries"), str): self.options["entries"] = json.loads(self.options["entries"])`. Apply same pattern to `record_types` for symmetry. The same class of bug exists in `AddFieldsToPageLayout` (encountered while investigating #3613): `cci task run add_page_layout_fields ... -o fields '[...]'` -> `pydantic.ValidationError: value is not a valid list`. A more general fix would be a helper in the CLI/task-base that auto-parses JSON strings for list-typed options, or schema-driven coercion via the new task_options Pydantic models.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3953.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3953:`).
