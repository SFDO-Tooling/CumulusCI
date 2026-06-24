# Fix sketch - #2979: deploy task should deploy from default entry in packageDirectories

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/2979>

## Bug

-   `cumulusci/cumulusci.yml:227-229` - the `deploy` task still hard-codes `path: src` for `cumulusci.tasks.salesforce.Deploy`. - `cumulusci/core/config/project_config.py:517-525` - `default_package_path` correctly reads `packageDirectories[*].default` from `sfdx-project.json` when `project__source_format == "sfdx"`. - The only consumer of `default_package_path` is `cumulusci/tasks/create_pack...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open`- feature still missing; davisagli's 2021 design comment (3-tier fallback`path`-> sfdx default ->`src`) remains the natural plan.

-   pass2 labels: `severity:low,area:packaging,area:sfdx,state:needs-design`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_2979.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #2979:`).
