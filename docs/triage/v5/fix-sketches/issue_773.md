# Fix sketch — #773: Document task return values and results

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `docs`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/773>

## Bug

Document task return values and results

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

1. Add a class attribute on `BaseTask`:

```python
return_values_schema: ClassVar[Dict[str, str]] = {}
```

where each key is the return-values dict key and each value is a one-line
description (parallel to how `task_options` already works).

2. Extend `doc_task()` in `cumulusci/utils/__init__.py` to render a
   "Return Values" RST section (heading + bullet list) when
   `task_class.return_values_schema` is non-empty. Update the matching
   `get_task_*` helpers to surface the schema for web-doc generation.

3. Backfill the schema on tasks that already emit return values — search
   for `self.return_values\[` across `cumulusci/tasks/`: at minimum
   `PackageUpload`, `PromotePackageVersion`, `GithubRelease`,
   `CreatePackageVersion`, dependency-resolution tasks. Each gets a few
   lines.

4. Lift the `attention` admonition in `docs/config.md:740-744` once
   coverage is broad enough.

Estimated effort: 1-2 day PR for the framework + first wave of tasks; an
ongoing "every new task documents its return values" contributor
expectation thereafter (enforce in `requesting-code-review` skill).

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_773.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #773:`).
