# Fix sketch — #3541: `None__dev` SFDX alias

**Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)
**Theme**: `keychain`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3541>

## Bug

-   `cumulusci/core/keychain/base_project_keychain.py` lines 77-79: - When `project_config.project__name` is None (cumulusci.yml without a `project.name`, or partially-loaded project_config), this f-string

## Target

`cumulusci/core/keychain/base_project_keychain.py:77-79`. Migration helper recommended to scan the keychain for `None__*` aliases and rewrite them once a real `project.name` is available.

## Recommended approach (from triage narrative)

-   **Approach**: Guard the alias construction. Two reasonable options:
    (1) raise `CumulusCIException("Cannot build sfdx_alias: project.name is not set in cumulusci.yml")` — surfaces the misconfiguration at the earliest possible moment.
    (2) Fall back to `f"{org_name}"` (no prefix) when `project__name` is None, with a `logger.warning`. Less disruptive for existing setups.
    Option 2 is the safer change; option 1 is the more correct one. Pick based on willingness to break first-run UX.

-   **Target**: `cumulusci/core/keychain/base_project_keychain.py:77-79`.
    Migration helper recommended to scan the keychain for `None__*` aliases
    and rewrite them once a real `project.name` is available.

-   **Size**: ~10 LOC for the guard, ~30 LOC including a one-shot migration
    pass on keychain load.

-   **Risk**: medium. Existing keychains in the wild may already contain
    `None__dev` rows; option 2 silently writes a new alias on next run,
    option 1 forces the user to fix cumulusci.yml. Document either way in
    CHANGELOG.

-   **API break**: no public API change. The `OrgConfig.sfdx_alias` field
    shape is preserved; only its derivation logic shifts.

-   **Bonus**: remove the `cannot-reproduce` label — the repro here is
    deterministic.

<!-- =============== R3 sub17 =============== -->

# Subagent 17 (docs) — Round 3 narrative

Worktree: `.worktrees/repro-docs` @ `1925a3083` (off `origin/dev`).
Issues processed: 3/3 (#773, #2500, #3464).
Verdict tally: 3 REPRODUCED-on-dev (all pure doc-gaps with code-level
testable assertions).

## Size & risk

| Field                                | Value                  |
| ------------------------------------ | ---------------------- |
| Size estimate                        | _TBD by fix-PR author_ |
| Risk                                 | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_                  |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_                  |
| Breaks public CLI surface            | _TBD_                  |

## Regression test

`cumulusci/tests/triage/test_issue_3541.py`. Remove the `@pytest.mark.xfail` marker and confirm green.

## Full narrative

See `docs/triage/v5/repro-results.md` (search for `### #3541:`).
