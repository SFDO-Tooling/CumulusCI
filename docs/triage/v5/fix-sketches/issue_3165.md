# Fix sketch - #3165: Update Admin Profile task fails when specifying record types without custom package.xml

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `metadata-etl`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3165>

## Bug

Update Admin Profile task fails when specifying record types without custom package.xml

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open` - single-line refactor.

-   pass2 labels: `bug` **Notes**: Smallest fix at update_profile.py:137 - always call `self._expand_package_xml_objects(package_xml)` regardless of `include_packaged_objects`, and only call the broader `self._expand_package_xml` (which does the Tooling API query) when `include_packaged_objects=True`. `_expand_package_xml_objects` itself only walks the user-supplied options, no API call.

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3165.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3165:`).
