# Fix sketch - #710: Allow disabling default scratch org configs

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `scratch-org-config`

**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/710>

## Bug

Allow disabling default scratch org configs

## Target

_See narrative for target file:line._

## Recommended approach (from triage narrative)

-   Approach: introduce a sentinel for "disabled" (recommend an explicit `disabled: true` flag on each scratch org config rather than relying on `config_file: None`, which has overloaded meaning) and skip disabled entries in `_load_scratch_orgs`. Optional: a stricter `merge_config` mode that preserves `None` overrides under `orgs.scratch.*`.

-   Target file:line: `cumulusci/utils/yaml/cumulusci_yml.py:147` (add `disabled: bool = None` to `ScratchOrg`); `cumulusci/core/keychain/base_project_keychain.py:155` (skip when `config.get("disabled")`); regenerate `cumulusci/schema/cumulusci.jsonschema.json`.
-   Size: small/medium.
-   Risk: low. Existing keys remain compatible; only adds new opt-in behaviour. Needs a docs note (`docs/orgs/scratch.md`) on how to disable inherited defaults.
-   API break: no (additive). The issue's literal `config_file: None` syntax would NOT be honoured under this proposal; if the team prefers that exact syntax instead, add a `dictmerge` exception so `None` overrides under `orgs.scratch.*` are preserved, then have `_load_scratch_orgs` skip entries with `config_file is None`. Either implementation satisfies the XFAIL test (`dev not in keychain.orgs`).

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_710.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #710:`).
