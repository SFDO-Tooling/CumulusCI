# Fix sketch - #3429: Support overriding `cumulusci.yml` to be used for configuration

**Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `packaging`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3429>

## Bug

-   `cumulusci/core/config/project_config.py:82` - `config_filename = "cumulusci.yml"` is hardcoded. - `cumulusci/core/config/project_config.py:118-184` - only an `additional_yaml` kwarg (programmatic, used by MetaCI) is supported; no env var or CLI plumbing. - `git merge-base --is-ancestor 9d650ace2 HEAD` returns non-zero - PR #3969 (commits prefixed `feat(cli): add resolve_extra_yaml helper ...

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   pass1: `keep-open`- feature is genuinely actionable on v4.10.0; auto-close once #3969 merges via`closed:fixed-by-pr-#3969`.

-   pass2 labels: `severity:medium,area:packaging,area:cli,state:in-progress`

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3429.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3429:`).
