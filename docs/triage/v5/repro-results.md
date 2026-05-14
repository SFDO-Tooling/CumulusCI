# Reproducibility Pass Results — Task 2.5c

## Scope

Two rounds of subagents:

-   **Round 1** (subagents 1-6): packaging + metadata-etl themes (45 issues; pre-v4.0.0 dropped per user; #3544 included as Cluster A canonical).
-   **Round 2** (subagents 7-12): cli + bulkdata + dependencies + ci-integration themes (53 issues; pre-v4.0.0 dropped; cross-theme dups assigned to one subagent).
-   **Total**: 98 of 142 open issues triaged via live v4.10.0 verification.
-   Method: each subagent in an isolated git worktree pinned to `origin/main` (= release v4.10.0 at commit `129238663`); per-bucket org provisioning via DevHub `CCIDevHub`.
-   See `themes.md` for the prior dry-run baseline; this file augments those proposals with v4.10.0 verdicts.

## Totals (98 issues)

| Verdict                                        | Count |
| ---------------------------------------------- | ----: |
| `REPRODUCED-on-v4.10.0`                        |    68 |
| `NOT-REPRODUCED-on-v4.10.0`                    |    18 |
| `INCONCLUSIVE-needs-cumulus-actions-workflow`  |     2 |
| `INCONCLUSIVE-needs-1gp-packaging-org`         |     1 |
| `INCONCLUSIVE-needs-2GP-CI-pipeline`           |     1 |
| `INCONCLUSIVE-needs-flaky-network`             |     1 |
| `INCONCLUSIVE-needs-live-cli-test`             |     1 |
| `INCONCLUSIVE-needs-managed-package-04t`       |     1 |
| `INCONCLUSIVE-needs-namespaced-project`        |     1 |
| `INCONCLUSIVE-needs-org-with-managed-package`  |     1 |
| `INCONCLUSIVE-needs-project-with-managed-deps` |     1 |
| `INCONCLUSIVE-needs-scratch-slot`              |     1 |
| `closed:duplicate-of-#3544`                    |     1 |

## Per-round tally

### Round 1 (packaging+metadata-etl, 45 issues)

| Verdict                                        | Count |
| ---------------------------------------------- | ----: |
| `REPRODUCED-on-v4.10.0`                        |    28 |
| `NOT-REPRODUCED-on-v4.10.0`                    |    10 |
| `INCONCLUSIVE-needs-1gp-packaging-org`         |     1 |
| `INCONCLUSIVE-needs-2GP-CI-pipeline`           |     1 |
| `INCONCLUSIVE-needs-cumulus-actions-workflow`  |     1 |
| `INCONCLUSIVE-needs-managed-package-04t`       |     1 |
| `INCONCLUSIVE-needs-namespaced-project`        |     1 |
| `INCONCLUSIVE-needs-project-with-managed-deps` |     1 |
| `closed:duplicate-of-#3544`                    |     1 |

### Round 2 (cli+bulkdata+dependencies+ci-integration, 53 issues)

| Verdict                                       | Count |
| --------------------------------------------- | ----: |
| `REPRODUCED-on-v4.10.0`                       |    40 |
| `NOT-REPRODUCED-on-v4.10.0`                   |     8 |
| `INCONCLUSIVE-needs-cumulus-actions-workflow` |     1 |
| `INCONCLUSIVE-needs-flaky-network`            |     1 |
| `INCONCLUSIVE-needs-live-cli-test`            |     1 |
| `INCONCLUSIVE-needs-org-with-managed-package` |     1 |
| `INCONCLUSIVE-needs-scratch-slot`             |     1 |

## Quick-action shortlist (high-confidence — proposed-pass1 deviates from dry-run baseline)

Subagents surfaced the following items where the v4.10.0 verdict suggests a clear change from the dry-run proposed action:

| #     | Theme                           | Verdict                                        | Subagent recommendation              | Note                                                                                         |
| ----- | ------------------------------- | ---------------------------------------------- | ------------------------------------ | -------------------------------------------------------------------------------------------- |
| #733  | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | runtime.py:131-133 still raises ClickException with same hard error message; no interactiv…  |
| #1348 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | No 'gitlab' or 'bitbucket' references anywhere in cumulusci/; ci_feature flow still uses g…  |
| #1350 | cli                             | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | project_config.py:52-57 sets up synthetic 'tasks' namespace package; include_source() at l…  |
| #1432 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | core/tasks.py:186-196 \_validate_options() only checks required; old-style task_options dic… |
| #1769 | bulkdata                        | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | Test code-smell: `lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf…  |
| #2096 | bulkdata                        | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | REST DML (`step.py:778-784 RestApiDmlOperation._record_to_json`) calls `process_bool_arg` …  |
| #2140 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | runtime.py get_org() calls keychain.get_org which raises OrgNotFound; cli/org.py:530-531 j…  |
| #2402 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | cli/flow.py:119-145 flow_run only has --delete-org flag; no --rebuild-org option; no rg ma…  |
| #2505 | bulkdata                        | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:feature-implemented`         | `MappingStep.soql_filter` field added (mapping_parser.py:120). `extract.py:142-147` applie…  |
| #2507 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | No undo_insert task in repo; bulkdata/load.py and snowfakery have enable_rollback option b…  |
| #2697 | cli                             | `INCONCLUSIVE-needs-scratch-slot`              | `closed:stale-24mo`                  | namespaced field is sourced from cci config not auto-derived from SFDX qa.json; keychain c…  |
| #3015 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | cli/org.py:519-543 org_remove always calls delete_org() if can_delete; no --keep-org or -o…  |
| #3024 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | Flow groups in cumulusci/cumulusci.yml still appear in original order: Metadata Transforma…  |
| #3161 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | flowrunner.py:317-320 \_obfuscate_if_sensitive masks if task_options info.sensitive==True; … |
| #3167 | metadata-etl                    | `NOT-REPRODUCED-on-v4.10.0`                    | `close-as-implemented`               | page*layout key on record_types is fully implemented in ProfileGrantAllAccess.\_set_record*… |
| #3283 | bulkdata                        | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:fixed-by-pr-#3361`           | PR #3361 (commit b0bfb70e0, "Support updates and upserts with blank dates represented by s…  |
| #3307 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | cli/project.py project_init only renders internal Jinja templates from cumulusci/files/tem…  |
| #3320 | metadata-etl                    | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:feature-implemented`         | deactivate_flow task is shipped in cumulusci/cumulusci.yml:10-15 using ActivateFlow class …  |
| #3347 | release-unlocked-beta-typeerror | `NOT-REPRODUCED-on-v4.10.0`                    | `close-with-comment`                 | create_package_version.py:158-159 now raises TaskOptionsError(PERSISTENT_ORG_ERROR) early …  |
| #3360 | bulkdata                        | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:feature-implemented`         | action: select was added by commit b15945203 (Aug 2024) — well before v4.10.0. select_util…  |
| #3466 | packaging                       | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:feature-implemented`         | RunApexTests in cumulusci/tasks/apex/testrunner.py exposes test_suite_names option (line 1…  |
| #3470 | cli                             | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | cumulusci.yml:823 only ci_master flow defined; no ci_main alias. davidmreed acknowledged b…  |
| #3479 | ci-integration                  | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | Reported error "Expecting value: line 1 column 1 (char 0)" is the bare json.JSONDecodeErro…  |
| #3561 | metadata-etl                    | `NOT-REPRODUCED-on-v4.10.0`                    | `close-as-fixed`                     | Bug was reported by yippie (who is also the PR author). Fix landed in commit 56e10665e (PR…  |
| #3605 | packaging                       | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:fixed-by-pr-#3651`           | PackageUpload (upload_production backing class) exposes major_version and minor_version op…  |
| #3607 | cli                             | `INCONCLUSIVE-needs-org-with-managed-package`  | `closed:stale-24mo`                  | Code path traced in cumulusci/tasks/apex/testrunner.py: retry_failures regex compiled at l…  |
| #3609 | cli                             | `INCONCLUSIVE-needs-live-cli-test`             | `closed:stale-24mo`                  | cumulusci/tasks/sfdx.py is now a thin shell wrapper around 'sf {command}' (SFDX_CLI = 'sf'…  |
| #3612 | cli                             | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | Issue is about the SFDO-Tooling/cci-vscode VSCode extension repo, not CumulusCI itself. Ou…  |
| #3615 | dependencies                    | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | `--resolution_strategy preproduction` is documented in cumulusci.yml as an alias for `late…  |
| #3699 | bulkdata                        | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | extract.py \_soql_for_mapping does not append ORDER BY. mapping_parser MappingStep has no o… |
| #3701 | bulkdata                        | `REPRODUCED-on-v4.10.0`                        | `closed:stale-24mo`                  | mapping_parser.py:171/190/228/241/422 special-case "Id" — it always represents the SF Id a…  |
| #3745 | packaging                       | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:stale-24mo`                  | latest*beta resolver looks up GitHub Releases (include_beta strategy) per install_package*…  |
| #3762 | metadata-etl                    | `closed:duplicate-of-#3544`                    | `close-as-duplicate`                 | Reporter (noahisapilot) explicitly self-identifies as duplicate of #3544 in their first co…  |
| #3884 | packaging                       | `INCONCLUSIVE-needs-project-with-managed-deps` | `closed:missing-fields`              | Source review: PackageNamespaceVersionDependency.install (dependencies.py L437-475) and Pa…  |
| #3929 | packaging                       | `NOT-REPRODUCED-on-v4.10.0`                    | `closed:not-reproducible-on-v4.10.0` | Ran create_community with name=TestWebsite template='Customer Service' url_path_prefix=tes…  |

## Per-subagent SUMMARY chunks

#### Bucket A — Packaging triage summary

Subagent 1 (`pkg-bucket-a`). Worktree pinned at `v4.10.0` / commit `129238663`.
10 issues processed; no GitHub mutations; no Salesforce org used.

#### Verdict counts

| Verdict                   | Count | Issues                                                 |
| ------------------------- | ----- | ------------------------------------------------------ |
| REPRODUCED-on-v4.10.0     | 8     | #2979, #3429, #3440, #3441, #3593, #3721, #3758, #3889 |
| NOT-REPRODUCED-on-v4.10.0 | 2     | #3466, #3605                                           |
| INCONCLUSIVE-\*           | 0     | —                                                      |
| SKIPPED                   | 0     | —                                                      |

#### Repro tests written (under `/tmp/repro/1/tests/`)

| Test file            | Purpose                                                                  | Result on v4.10.0            |
| -------------------- | ------------------------------------------------------------------------ | ---------------------------- |
| `test_issue_3466.py` | confirms `test_suite_names` option exists on `RunApexTests`              | passes (feature implemented) |
| `test_issue_3593.py` | demonstrates `SFDXOrgTask` still appends `-o <username>` unconditionally | fails (bug present)          |
| `test_issue_3605.py` | confirms `major_version`/`minor_version` exist on `PackageUpload`        | passes (feature implemented) |
| `test_issue_3758.py` | asserts `push_upgrade_org` final step calls `config_managed`             | fails (bug present)          |

`#2979`, `#3429`, `#3440`, `#3441`, `#3721`, `#3889` are all features whose absence is verifiable purely by code inspection (no test scaffolding needed); see `narrative.md` for `path:line` evidence.

#### Pass-1 recommended actions

| Recommendation               | Issues                                                 |
| ---------------------------- | ------------------------------------------------------ |
| `keep-open`                  | #2979, #3429, #3440, #3441, #3593, #3721, #3758, #3889 |
| `closed:feature-implemented` | #3466                                                  |
| `closed:fixed-by-pr-#3651`   | #3605                                                  |

#### Cross-cutting findings

1. **Multi-package SFDX umbrella (#2979, #3429, #3440)** — three open enhancements all point at the same gap: CumulusCI assumes a single package per repo. `default_package_path` exists but is only consumed by `create_package_version`. A single small design refactor (Deploy gets a `path: $project_config.default_package_path` default, `default_package_path` becomes name-aware, and a `cumulusci.yml` override mechanism is added) could resolve all three. Worth folding them into one umbrella issue or theme on the pass-2 labeling pass.

2. **Null/sentinel overrides in flow steps (#3441)** — yippie's comment generalizes the request: CCI lacks any way to "unset" or "reset to default" an option that a flow step has set. This is a CCI-wide ergonomics gap (not just `version_base`), and probably belongs as its own meta-issue.

3. **PR #3969 (`extra-yaml-cli-flag`) is in flight for #3429** — adds `--extra-yaml` and `CUMULUSCI_EXTRA_YAML`. Not yet in v4.10.0. Recommend the parent agent flip #3429 to `closed:fixed-by-pr-#3969` once that PR merges; until then `keep-open` is correct.

4. **muselab-d2x fork has a fix for #3721** — commit `7aaf348f3` ("Change version naming on PackageUpload task to use the predicted version number and a jinja2 template expression") implements jinja2 templating for `PackageUpload.version_name`. Lives only on `d2x/*` remotes. Could be ported upstream as a small PR; would also need a sibling change in `create_package_version.py:184` for 2GP coverage.

5. **One-line YAML fix candidate (#3758)** — `push_upgrade_org` last step should be `config_managed`, not `config_qa`. Currently both expand to the same task list, so it's not a behavior regression today, but the docs link customers to the wrong page. Excellent `good-first-issue` for an external contributor; explicitly out of scope for this triage pass.

6. **`SFDXOrgTask` org-flag append (#3593)** — recurring pain point as sf cli surface evolves; a generic `pass_org` / `no_org` opt-out option (or a curated whitelist of no-org subcommands) is a more durable fix than the user's `#` workaround. Verifying actual sf cli behavior of `project convert source` would need an org/sf cli; the CCI side of the bug is unchanged on v4.10.0.

7. **2GP unlocked uninstall (#3889)** — natural shape is a new `UninstallPackageVersion` task that calls Tooling API `SubscriberPackageVersion` delete directly, avoiding the sf cli stability concern the user calls out. Aligns with broader 2GP investment.

#### Bucket A — metadata-etl summary (Subagent 2)

**Worktree**: `/Users/jestevez/work/rel/CumulusCI/.worktrees/repro-etl-bucket-a`
**Pinned commit**: `129238663` (Release v4.10.0)
**Issues processed**: 11 / 11

#### Verdict counts

| verdict                   | count | issues                                                               |
| ------------------------- | ----- | -------------------------------------------------------------------- |
| REPRODUCED-on-v4.10.0     | 10    | #3137, #3331, #3518, #3543, #3585, #3692, #3771, #3773, #3938, #3939 |
| NOT-REPRODUCED-on-v4.10.0 | 1     | #3320                                                                |
| INCONCLUSIVE              | 0     | —                                                                    |
| SKIPPED                   | 0     | —                                                                    |

#### Severity / urgency picks (most worth flagging in pass-1)

-   **#3938 (CRITICAL, recently filed 2025-12-16)** — `rest_deploy: True` silently
    swallows failed deployments and reports success. Affects MetaDeploy plans
    and any flow using `rest_deploy`. Same reporter as #3939; likely both
    blocking the same production-deploy workflow.
-   **#3939 (HIGH, recently filed 2025-12-16)** — Even SOAP-path deploys lose
    their actual error text because `BaseMetadataApiCall.__call__` wraps every
    exception in the generic "Could not process MDAPI response" message.
    Apex test failures, component failures, and API errors are all clobbered.
-   **#3518 (HIGH)** — `add_picklist_entries` always marks a default for record
    types because of a missing `()` after `.lower` (picklists.py:177); blocks
    any non-default picklist additions on objects with record types.

#### Cross-cutting findings

-   **Error-handling pattern (#3938 + #3939)**: Both critical bugs come from
    the same anti-pattern — an outer try/except at the orchestration layer
    swallows exceptions raised by inner code that was correctly trying to
    surface a user-actionable error. Worth a single PR that audits both
    code paths and keeps `CumulusCIException` subclasses unwrapped.
-   **`metadata_map.yml` accuracy (#3331 + #3692 + arguably #3585)**: Three
    separate bugs trace back to the YAML metadata-name registry being
    out-of-date or inconsistent: wrong type name (`AssignmentRule` vs
    `AssignmentRules`), missing entry (`digitalExperiences`), and lack of
    parser robustness against newer SFDX-emitted XML quirks (`xsi:nil="true"`).
    A single sweep against the current MDAPI catalog would close all three.
-   **External fork PR for #3771**: Commit `2bf6ce6a3` ("Improve namespace
    handling in find_replace") exists on `remotes/leboff/...` but never
    landed on origin/main. Bringing that PR back through review would close
    the issue.
-   **#3320 mismatch**: Reporter asked for a `deactivate_flow` task; one is
    already shipped in `cumulusci/cumulusci.yml:10-15`. Likely a docs /
    discoverability issue rather than a code one — worth flagging in pass-2
    as `closed:feature-implemented` plus a small doc improvement.
-   **Architectural gap for #3773**: `RetrieveProfileApi._queries_retrieve_permissions`
    doesn't query `FieldPermissions` at all. This is a class-of-omission
    bug: any object that has profile field-perms but no object-perms
    (very common for standard objects like `AccountContactRelation`) is
    silently dropped. Likely there are other under-queried permission
    surfaces too — worth a focused review.

#### Output artifacts

-   `/tmp/repro/2/repro-results.csv` — machine-readable results (12 rows)
-   `/tmp/repro/2/narrative.md` — per-issue evidence and recommended actions
-   `/tmp/repro/2/tests/test_issues_bucket_a.py` — 11 throwaway repro tests;
    all 11 currently fail on v4.10.0 (= bugs reproduced).

#### Constraint compliance

-   No `git push` from worktree.
-   No GitHub mutations (only read-only inspection of bundled JSON).
-   No writes under `cumulusci/robotframework/`.
-   All repro tests live under `/tmp/repro/2/tests/`, not in the worktree
    source tree.
-   No third-party packages added; tests use only `pytest`, `pyyaml`, and
    in-tree CCI modules.
-   `uv run pytest ...` used for test execution.

#

**Theme**: packaging
**Bucket**: B (scratch-org-required)
**Worktree**: `.worktrees/repro-pkg-bucket-b1` @ `129238663` (release v4.10.0)
**Issues processed**: 6 / 6

#### Verdict tally

| Verdict                                           | Count | Issues       |
| ------------------------------------------------- | ----- | ------------ |
| REPRODUCED-on-v4.10.0                             | 2     | #3446, #3734 |
| NOT-REPRODUCED-on-v4.10.0 (feature unimplemented) | 2     | #3587, #3600 |
| INCONCLUSIVE-needs-cumulus-actions-workflow       | 1     | #3418        |
| INCONCLUSIVE-needs-2GP-CI-pipeline                | 1     | #3542        |
| **Total**                                         | **6** |              |

#### Recommended pass1 actions

| Issue | Action    | Reasoning                                                          |
| ----- | --------- | ------------------------------------------------------------------ |
| #3418 | unchanged | external github action; needs cross-repo investigation             |
| #3446 | keep-open | reproduced; simple fix (validate version) + UX (Push API guidance) |
| #3542 | unchanged | external CI/CD; needs reporter info on workflow SHA semantics      |
| #3587 | keep-open | feature still missing; small enhancement                           |
| #3600 | keep-open | feature still missing; needs design decision on syntax             |
| #3734 | keep-open | reproduced; remove stale `cannot-reproduce` label                  |

#### Cross-cutting findings

1. **Two clear bugs reproducing on v4.10.0 (#3446, #3734)** with well-localized root causes:
    - #3446 is a missing-validation bug in `cumulusci/tasks/push/tasks.py` `_run_task` / `_parse_version`.
    - #3734 is a logic bug in `cumulusci/tasks/salesforce/package_upload.py` `_validate_versions` where a Beta patch on a previous minor is treated as the latest version.
2. **Two unimplemented features (#3587, #3600)** suitable for "good-first-issue" tagging:
    - #3587 wants a one-line warning in `UpdatePackageXml._init_task`.
    - #3600 wants env-var substitution in task options — broader scope (touches all options, not just `install_managed`); needs design.
3. **Two issues that escape cci's repo boundary (#3418, #3542)**:
    - #3418 is in `SFDO-Community/standard-workflows`; cci has no `auth:sfdxurl:store` code path.
    - #3542 is a SHA-mismatch problem between the workflow that posts a commit status and the local checkout that reads it; could be fixed in `cumulus-actions/standard-workflows` or by adding a parent-commit fallback in `get_version_id_from_commit`.
4. **Mislabeled triage state on #3734**: the user's last three comments contain a correct, fully-localized root-cause analysis. The `cannot-reproduce` and `awaiting-more-details` labels are stale and should be dropped in pass2 in favor of `bug`.
5. **Code stability**: none of the relevant code paths for these six issues have changed materially between the issue dates and v4.10.0 (verified via `git log` for `cumulusci/tasks/push/`, `cumulusci/tasks/salesforce/package_upload.py`, `cumulusci/tasks/github/commit_status.py`, `cumulusci/tasks/metadata/package.py`, `cumulusci/utils/yaml/safer_loader.py`, `cumulusci/core/tasks.py`).

#### Scratch orgs used

-   `repro-pkg-b1-dev` (cci alias) / `CumulusCI__repro-pkg-b1-dev` (sf alias) — config `dev`, used for live `install_managed` and `push_qa` invocations.

No second alias was needed; `feature` config was not required.

#### Cleanup status

**Cleanup completed successfully**. Verified at end of session:

```
$ uv run cci org list 2>&1 | grep -i 'pkg-b1'
  (no rows match)
$ sf org list 2>&1 | grep -i 'pkg-b1'
  (no rows match)
```

Steps taken:

1. `uv run cci org scratch_delete repro-pkg-b1-dev` — sf-side org deleted via `sf org delete scratch -p -o test-ra9moqy3oqup@example.com`.
2. `uv run cci org remove repro-pkg-b1-dev` — cci keychain alias removed (cci was still listing the alias even after `scratch_delete` because the alias entry persists locally).

#### Output files (under `/tmp/repro/3/`)

-   `repro-results.csv` — one row per issue (header + 6 data rows).
-   `narrative.md` — per-issue method/evidence/recommendation.
-   `tests/repro_3446_push_qa_no_version.py` — reproduces NoneType.split.
-   `tests/repro_3587_update_package_xml_no_warning.py` — confirms install_class silently dropped.
-   `tests/repro_3600_install_managed_no_env_var.py` — confirms no env-var substitution.
-   `tests/repro_3734_upload_production_beta_patch.py` — confirms Beta-patch sets colliding minor.

#### Deviations from constraints

None.

#

#### Verdict tally (5 issues processed)

| Verdict                                        | Count | Issues       |
| ---------------------------------------------- | ----- | ------------ |
| `REPRODUCED-on-v4.10.0`                        | 1     | #3746        |
| `NOT-REPRODUCED-on-v4.10.0`                    | 2     | #3745, #3929 |
| `INCONCLUSIVE-needs-project-with-managed-deps` | 1     | #3884        |
| `INCONCLUSIVE-needs-1gp-packaging-org`         | 1     | #3899        |
| `SKIPPED-policy-*`                             | 0     | —            |

Total: 5 / 5 (100%).

#### Cross-cutting findings

1. **Two of five issues had already self-resolved upstream**: #3745 (user-confusion about ci_beta requiring release_2gp_beta to publish the GitHub release tag — accepted by the reporter in-thread) and #3929 (an upstream Salesforce CLI / Communities API bug that is now fixed per OP comment 2025-10-22 and confirmed end-to-end against scratch org). The triage policy's stale-24mo and needs-repro proposals respectively were defensible at proposal time but #3929 should now flip to `closed:not-reproducible-on-v4.10.0`.

2. **One real, trivially-fixable v4.10 bug surfaced**: #3746 (`create_package_version._get_base_version_number` SOQL has no `IsDeprecated = false` filter). The same file has the filter on a parallel `Package2` lookup at line 297, so the omission at line 535 is asymmetric and the fix is one clause. This is a `target:v4-patch` candidate hidden under a stale-24mo proposal.

3. **One issue is provably an upstream Salesforce platform bug, not CCI**: #3899. The reported error (`system.scheduler.cron.JobType.getJobImplementation()` being null) references Salesforce-internal Java classes; CCI sends correct Apex; trivial Apex runs cleanly on a fresh scratch org. The triage labelling vocabulary should grow an `external/upstream-salesforce` Pass-2 label so future triage can disposition this class of report quickly.

4. **One issue is plausibly user-misperception of log noise**: #3884 (dev_org "reinstalls" same package version). Source review confirms skip-if-already-installed logic is present in v4.10.0 for both managed-package install paths. Without a customer project that has managed deps, we cannot disprove a corner case, but the proposed `closed:missing-fields` (rule 3) is the right disposition because the report lacks the `cumulusci.yml` excerpt that would let us identify which dependency type they observed.

5. **Methodology note**: 2 of 5 verdicts were reachable by code review alone (#3745, #3746), 1 required a brief scratch-org runtime check that succeeded (#3899 partial; #3929 full), and 1 required a runtime check that fully resolved the question (#3929). The scratch org was reused across all runs — quota cost: 1 dev-config scratch (already provisioned, not torn down per "Scratch org cleanup" below since other subagents may still be relying on the DevHub quota math).

#### Scratch org aliases used

-   `repro-pkg-b2-dev` (config: `orgs/dev.json`, expires 2026-05-15 08:51 PT, instance `customization-java-47-dev-ed.scratch`).
    -   Used for: #3899 unschedule_apex runtime check, #3929 create_community runtime check.
    -   Already existed at session start (presumably from a prior controller run); reused, not recreated, so no fresh DevHub-create quota was consumed by this subagent.

#### Output files written

-   [`/tmp/repro/4/repro-results.csv`](/tmp/repro/4/repro-results.csv) — 5 rows + header, full triage CSV schema per plan §2.5c step 5.
-   [`/tmp/repro/4/narrative.md`](/tmp/repro/4/narrative.md) — per-issue narrative, sorted by verdict (REPRODUCED first).
-   [`/tmp/repro/4/SUMMARY.md`](/tmp/repro/4/SUMMARY.md) — this file.
-   [`/tmp/repro/4/evidence/`](/tmp/repro/4/evidence/) — 5 evidence files, one per issue, referenced from `repro-results.csv` and `narrative.md`.

#### Deviations from the prompt

-   The scratch org `repro-pkg-b2-dev` was already provisioned at session start (left over from a prior run, healthy and unexpired). Reused it directly rather than creating a new one. Documented above; conserves DevHub quota.
-   Cleanup decision deferred to the controller — see "Scratch org cleanup" note below.

#### Scratch org cleanup (executed)

```
$ uv run cci org scratch_delete repro-pkg-b2-dev
[05/14/26 02:07:26] Deleting scratch org with command: sf org delete scratch -p
                    -o test-qu66hqqypnu3@example.com
[05/14/26 02:07:28] (success)

$ uv run cci org remove repro-pkg-b2-dev
(silently removes the cci keychain entry)

$ sf org list scratch --target-dev-hub CCIDevHub | grep qu66hqqypnu3 || echo "absent"
absent

$ uv run cci org list | grep repro-pkg-b2 || echo "absent"
absent
```

DevHub `CCIDevHub` quota slot returned. No worktree branch pushed. No GitHub mutations performed. No files written under `cumulusci/robotframework/`.

#

Theme: **metadata-etl** · Bucket **B** · Worktree `.worktrees/repro-etl-bucket-b` @ commit `129238663` (release v4.10.0)

#### Verdict tally (10 issues processed)

| Verdict                                     | Count | Issues                                           |
| ------------------------------------------- | ----- | ------------------------------------------------ |
| REPRODUCED-on-v4.10.0                       | 7     | #808, #2826, #3165, #3613, #3931, #3951, #3953   |
| NOT-REPRODUCED-on-v4.10.0 (already fixed)   | 1     | #3561 (fix in PR #3566, May 2024)                |
| NOT-REPRODUCED-on-v4.10.0 (feature shipped) | 1     | #3167 (PR #3243, June 2022)                      |
| closed:duplicate                            | 1     | #3762 (dup of #3544; self-confirmed by reporter) |

Of the 7 REPRODUCED:

-   4 are real correctness bugs (#808, #2826, #3165, #3931)
-   2 are UX/error-message bugs (#3613, #3951) — underlying functionality works with correct input
-   1 is a CLI option-parsing bug (#3953) — task is unusable from CLI

#### Cross-cutting findings

##### 1. CLI doesn't auto-parse JSON list options for several ETL tasks

`AddPicklistEntries.entries`, `AddFieldsToPageLayout.fields/pages`, and likely other dict-list options can be set in `cumulusci.yml` (where the YAML loader parses them into lists/dicts) but break from the CLI when passed as JSON strings. Each task currently has to re-implement parsing if it wants to support CLI use.

Issues affected: **#3953** (confirmed) and **add_page_layout_fields** (found while testing #3613).

Likely fix venues:

-   One-line `json.loads` in each affected task's `_init_options`. Cheap, low risk.
-   Or: a generic helper on `BaseTask._init_options` that walks `task_options` declared as list/dict and JSON-parses string values. Higher impact, deeper change.
-   Or: leverage Pydantic-validated `task_options` (already used in `AddFieldsToPageLayout` for `AddFieldsToLayoutOptions`) to coerce strings -> JSON via a validator.

##### 2. `MetadataSingleEntityTransformTask` "Cannot find metadata file" error is unhelpful

`MetadataSingleEntityTransformTask._transform` (base.py:332) raises a generic message when the user-provided `api_names` value doesn't match any retrieved file. Shared root cause behind **#3613** (Layout) and **#3951** (DuplicateRule), and probably also explains user confusion with other entities like `Profile`, `Flow`, `RecordType` whose Metadata API names follow non-obvious patterns.

Suggested fix: when the file is missing, also log the list of files actually retrieved into `source_metadata_dir`. Single change, multi-issue improvement.

##### 3. `update_admin_profile`'s `record_types` plus `_expand_package_xml` gating is fragile

The `record_types` -> `_expand_package_xml_objects` dependency is buried inside `_expand_package_xml`, which is gated on `include_packaged_objects=True`. This means a user who specifies `record_types` for an object outside the default `admin_profile.xml` package list — without also setting `include_packaged_objects: true` — silently skips the package.xml expansion needed for their record types.

Issues affected: **#3165** (record_type for Case fails). Probably also a contributing factor in **#3544 / #3762** (the namespaced-org Person Accounts crash).

The fix is a one-line refactor: always call `_expand_package_xml_objects` (which only walks the user's options); only call the full `_expand_package_xml` (Tooling API query) when `include_packaged_objects=True`.

##### 4. Several issues are "long-tail" enhancement requests still open

**#808** (2018), **#2826** (2021), **#3167** (2022, now implemented), **#3561** (2023, now fixed). The pattern suggests value in periodic dup/staleness sweeps that pair issues with PRs (#3167 ↔ #3243, #3561 ↔ #3566) — both were closed by a PR but the issue was never auto-closed.

#### Scratch org aliases used

-   `repro-etl-b-dev` — used for live repros of #3613, #3951, #3953. Pre-existed from a prior subagent setup; reused as instructed. Will be deleted in the cleanup step. Created 2026-05-14 with `dev.json`, expires 2026-05-15.

No additional scratch orgs created.

#### Output files

-   `/tmp/repro/5/repro-results.csv` — verdict CSV (10 rows + header)
-   `/tmp/repro/5/narrative.md` — per-issue narrative (10 sections)
-   `/tmp/repro/5/SUMMARY.md` — this file
-   `/tmp/repro/5/tests/issue-2826/repro_unit.py` — Python repro (FileNotFoundError)
-   `/tmp/repro/5/tests/issue-3165/repro_unit.py` — Python repro (package.xml expansion gap)
-   `/tmp/repro/5/tests/issue-3613/output-just-object.txt` — CLI output (Cannot find metadata file)
-   `/tmp/repro/5/tests/issue-3613/output-good-name.txt` — CLI output (success with correct API name)
-   `/tmp/repro/5/tests/issue-3931/repro_unit.py` — Python repro (NoneType.text)
-   `/tmp/repro/5/tests/issue-3931/repro-output.txt` — captured output
-   `/tmp/repro/5/tests/issue-3951/output-no-prefix.txt` — CLI output (Cannot find metadata file)
-   `/tmp/repro/5/tests/issue-3953/output.txt` — CLI output (fullName key required)

#### Deviations

None. All 10 issues processed within the protocol. No GitHub mutations. No commits to the worktree. No edits to `cumulusci/robotframework/`. No `git push`. No package additions to `pyproject.toml`/`uv.lock`.

#

#### Verdict tally

| Verdict                                  | Count | Issues |
| ---------------------------------------- | ----- | ------ |
| `NOT-REPRODUCED-on-v4.10.0`              | 1     | #3347  |
| `INCONCLUSIVE-needs-managed-package-04t` | 1     | #3902  |
| `INCONCLUSIVE-needs-namespaced-project`  | 1     | #3544  |
| `REPRODUCED-on-v4.10.0`                  | 0     | —      |
| **Total processed**                      | **3** |        |

#### Scratch org aliases used

| Alias                | Config            | DevHub    | Status                                                                         |
| -------------------- | ----------------- | --------- | ------------------------------------------------------------------------------ |
| `repro-special-c-pa` | `person_accounts` | CCIDevHub | Created (existed at session start, reused), used for #3544, slated for cleanup |

No other aliases created. #3902 and #3347 were code-only investigations.

#### Per-issue outcomes

##### #3347 — `release_unlocked_beta` TypeError → fixed

Cryptic `TypeError: expected str, bytes or os.PathLike object, not NoneType` is replaced on v4.10.0 by an early `TaskOptionsError(PERSISTENT_ORG_ERROR)` at `cumulusci/tasks/create_package_version.py:158-159`, fix landed in commit `2a9cadcb1` (2023-10-12). Existing test `test_create_package_version.py::TestPackageConfig::test_org_config` validates the new behavior and passes. **Recommend close-with-comment.**

##### #3902 — `install_managed` security_type with 04t → code looks correct, runtime not validatable

Code path inspection on v4.10.0 confirms `install_managed` faithfully passes `security_type` to the Salesforce Tooling API `PackageInstallRequest.SecurityType` for both 04t and namespace+version code paths. `SecurityType.ADMIN` correctly serializes to JSON `"NONE"`. No CumulusCI defect identified; observed user behavior likely originates from Salesforce platform behavior (upgrade vs fresh install, App-level tab visibility, etc.). **Cannot fully validate without a reusable managed package 04t fixture — verdict INCONCLUSIVE-needs-managed-package-04t.**

##### #3544 — `update_admin_profile` with PersonAccounts + namespacing → not validatable in CumulusCI repo

Bug requires the intersection of PersonAccounts AND a namespaced project. CumulusCI itself has no project namespace, so the repro condition cannot be fully satisfied without registering a namespace in CCIDevHub (out of scope). Partial repro: `update_admin_profile` ran SUCCESSFULLY against a non-namespaced PersonAccounts scratch on v4.10.0, confirming the bug is specific to the namespaced+PersonAccounts intersection. No code-level fix found referencing #3544 / W-12589033 in `update_profile.py` since 2023. **Verdict INCONCLUSIVE-needs-namespaced-project.**

#### Per-issue blocker explanations

| Issue | Blocker                                                                                   | Mitigation                                                                              |
| ----- | ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| #3347 | None — code-only verifiable                                                               | Existing pytest passes on HEAD                                                          |
| #3902 | No reusable managed package 04t fixture available within CCIDevHub workflow               | Recommend Pass 2 label `needs-managed-package-fixture`                                  |
| #3544 | CumulusCI repo has no project namespace; cannot satisfy `namespaced:true` repro condition | Recommend Pass 2 label `needs-namespaced-project` and ask reporter to retest on v4.10.0 |

#### Adjacent finding (not in scope but worth recording)

While exercising `-o namespaced_org True` on a non-namespaced project for #3544, surfaced a latent `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` at `cumulusci/utils/__init__.py:229`:

```229:229:cumulusci/utils/__init__.py
    namespaced_org = namespace + "__" if namespaced_org else ""
```

Distinct from #3544 (init-time vs deploy-time). Suggest a separate small cleanup ticket.

#### Outputs

-   `/tmp/repro/6/repro-results.csv` — header-conforming CSV with 3 rows
-   `/tmp/repro/6/narrative.md` — per-issue narrative sections
-   `/tmp/repro/6/SUMMARY.md` — this file
-   `/tmp/repro/6/tests/` — directory created but no new test files written (used existing in-repo test for #3347; manual cci command for #3544; pure code inspection for #3902)

#### Constraints honored

-   No `git push` from worktree.
-   No GitHub mutations.
-   No edits under `cumulusci/robotframework/`.
-   No edits to `pyproject.toml`/`uv.lock`.
-   All commands run via `uv run …` from the worktree.
-   DevHub: `CCIDevHub` only.
-   Scratch alias prefix: `repro-special-c-`.

#

Worktree: `.worktrees/repro-cli-part1` @ `129238663` = release v4.10.0.

#### Verdict tally (13 issues)

| Verdict                         | Count | Issues                                                                     |
| ------------------------------- | ----- | -------------------------------------------------------------------------- |
| REPRODUCED-on-v4.10.0           | 11    | #733, #1348, #1432, #2140, #2402, #2507, #3015, #3024, #3161, #3307, #3470 |
| NOT-REPRODUCED-on-v4.10.0       | 1     | #1350                                                                      |
| INCONCLUSIVE-needs-scratch-slot | 1     | #2697                                                                      |

By type: 10 features, 3 bugs (one of which is partially-fixed: #1432; one fully-fixed: #1350; one inconclusive: #2697).

#### Recommended pass1 labels

| Recommendation                                  | Count | Issues           |
| ----------------------------------------------- | ----- | ---------------- |
| `closed:stale-24mo` (confirms dry-run proposal) | 12    | all except #1350 |
| `closed:not-reproducible-on-v4.10.0`            | 1     | #1350            |

So **12 of 13 dry-run `closed:stale-24mo` proposals stand**. One should be re-categorised as `closed:not-reproducible-on-v4.10.0` (#1350).

#### Cross-cutting findings

1. **Most of the bundle is stable feature requests with very little movement** (#733 from 2018, #1348 from 2019, #2140 from 2020, etc.). The `closed:stale-24mo` action is appropriate; the work-items in some cases (W-028291, W-10502624, W-10502512) have been tracked for years without delivery.

2. **#1350 is the only clear "we shipped a fix" issue**: a synthetic `tasks` namespace package was added (`cumulusci/core/config/project_config.py:52-57`) plus `_add_tasks_directory_to_python_path()` so cross-project task imports now resolve. The follow-up _name-collision_ concern raised by `prescod` in 2022 is a separate concern and would warrant its own issue if anyone hit it again.

3. **#1432 and #2507 and #3161 each show "partial mitigation"** — infrastructure has landed but the original ergonomic request is not fully satisfied. Worth flagging in `notes` so these don't get re-triaged as still-open feature debt without context. Adding `partially-fixed` / `partially-implemented` labels in pass2 surfaces this.

4. **Inclusive-language angle (#3470)**: the rename remains undone but the underlying need (flow aliasing) is acknowledged. If pass2 includes a `inclusive-language` label, this is the only candidate.

5. **No issues should remain open** — all 13 are either fixed, stale, or design-as-intended (the design-as-intended one, #2697, is best closed with a `needs-info` framing if anyone reopens).

#### Scratch org aliases used

**No scratch needed**. All 13 issues were resolved via code-scan (Bucket A) plus one unit test. #2697 was the only candidate for Bucket B and the code reading was conclusive enough to defer scratch provisioning (DevHub-slot conservation per instructions).

#### Output files

-   `/tmp/repro/7/repro-results.csv` — 13 rows, header included.
-   `/tmp/repro/7/narrative.md` — H3 section per issue.
-   `/tmp/repro/7/SUMMARY.md` — this file.
-   `/tmp/repro/7/tests/test_1432_options_validation.py` — unit repro for #1432 (passes on v4.10.0).

#### Deviations

None.

#

**Pinned commit**: `129238663` (Release v4.10.0)
**Branch**: `worktree/repro/cli-part2`
**Worktree**: `.worktrees/repro-cli-part2`
**Issues processed**: 13 / 13
**Scratch orgs provisioned**: none — all repros completed via Bucket A (code-scan + one isolated unit test)

#### Verdict tally

| Verdict                                     | Count | Issues                                                               |
| ------------------------------------------- | ----- | -------------------------------------------------------------------- |
| REPRODUCED-on-v4.10.0                       | 10    | #3485, #3492, #3506, #3549, #3570, #3618, #3663, #3754, #3852, #3854 |
| INCONCLUSIVE-needs-org-with-managed-package | 1     | #3607                                                                |
| INCONCLUSIVE-needs-live-cli-test            | 1     | #3609                                                                |
| NOT-REPRODUCED-on-v4.10.0                   | 1     | #3612                                                                |

#### Pass-1 recommendation tally

| Recommendation                       | Count | Issues                                                               |
| ------------------------------------ | ----- | -------------------------------------------------------------------- |
| `keep-open`                          | 10    | #3485, #3492, #3506, #3549, #3570, #3618, #3663, #3754, #3852, #3854 |
| `closed:stale-24mo`                  | 2     | #3607, #3609                                                         |
| `closed:not-reproducible-on-v4.10.0` | 1     | #3612                                                                |

Both kept-open issues from the dry-run (#3852, #3854) remain `keep-open` here — verdicts confirm the maintainer's label.

#### Cross-cutting findings

1. **Flow `when:` clause is structurally limited.** Three issues in this batch (#3506, #3570, #3663) all expose the same surface: the `when:` evaluator at `cumulusci/core/flowrunner.py:510-516` only sees `project_config` + `org_config`, and `when:` is only honored on `task:` steps (line 669) — never on `flow:` steps (lines 674-697). A single epic could absorb #3506 + #3663 and is adjacent to #3570's "finally/error path" request.

2. **`-o` / option-parsing surface is rigid.** #3492 (project-level overrides) and #3618 (multi-org operations) are both small CLI parser improvements. Both landed in this batch with `keep-open` and `good-first-issue`-eligible scope.

3. **JUnit/test-output story for Apex is half-done.** #3485 (malformed JUnit from `run_tests`) and #3549 (no test output from `deploy`) both concern producing CI-consumable test results. A consistent JUnit emitter shared by both tasks would close both.

4. **Update-check / network-dependence concerns.** #3754 (no way to disable PyPI ping) is small and self-contained. Adding a `CUMULUSCI_DISABLE_VERSION_CHECK` env var around `cumulusci/cli/utils.py:check_latest_version` (line 82) closes it in one short PR.

5. **Two genuine regressions are still active**:

    - #3852 (sarge `Capture.flush`) is upstream-dependent (sarge 0.1.8 unreleased). Cosmetic only on Python 3.13.
    - #3854 (`capture_sample_data` validation) is a regression introduced by PR #3741 / `2c5d0056e`. Workaround documented (downgrade to 3.84.1) but the bug is real for polymorphic-lookup users.

6. **#3609 (dx plugins:install) is upstream-only.** `cumulusci/tasks/sfdx.py` is now a 5-line shell wrapper around `sf {command}`; any `Timed out` error originates in the SF CLI itself.

7. **#3612 belongs in a different repo** (`SFDO-Tooling/cci-vscode`) and should be transferred or closed as wrong-repo.

#### Output files

-   `/tmp/repro/8/repro-results.csv` — 13 rows, header validated, parses cleanly.
-   `/tmp/repro/8/narrative.md` — H3 section per issue with verdict + evidence + pass-1/pass-2 recs.
-   `/tmp/repro/8/SUMMARY.md` — this file.
-   `/tmp/repro/8/tests/test_3607_retry.py` — one repro test (passes, confirming retry regex logic is correct in isolation).

#### Scratch-org cleanup

No scratch orgs provisioned — Bucket A sufficed for all 13. Nothing to delete.

#### Deviations

None.

#

**Theme**: bulkdata · **Bucket**: B (org-eligible) · **Pinned commit**: `129238663` (= release v4.10.0) · **Issues processed**: 9 / 9

#### Verdict tally

| Verdict                   | Count | Issues                                   |
| ------------------------- | ----- | ---------------------------------------- |
| REPRODUCED-on-v4.10.0     | 6     | #1769, #2013, #2325, #2506, #2508, #2951 |
| NOT-REPRODUCED-on-v4.10.0 | 3     | #2096, #2505, #3283                      |
| INCONCLUSIVE              | 0     | —                                        |

#### Pass-1 recommendations

| Recommendation                     | Count | Issues                            |
| ---------------------------------- | ----- | --------------------------------- |
| keep-open                          | 5     | #2013, #2325, #2506, #2508, #2951 |
| closed:not-reproducible-on-v4.10.0 | 1     | #2096                             |
| closed:feature-implemented         | 1     | #2505                             |
| closed:fixed-by-pr-#3361           | 1     | #3283                             |
| closed:stale-24mo                  | 1     | #1769                             |

#### Bug vs. feature

-   5 bugs: #1769 (test code-smell), #2013 (extract multi-step duplicate table), #2096 (REST booleans), #2951 (Pricebook sequencing), #3283 (empty date).
-   4 features: #2325 (validation rule toggle), #2505 (extract WHERE), #2506 (debug tempfiles), #2508 (manual retries).

#### Cross-cutting findings

1. **Pattern of extending metadata-toggle tasks is fertile**: `disable_tdtm_trigger_handlers`, `restore_tdtm_trigger_handlers`, `set_duplicate_rule_status` form a clear template (`MetadataSingleEntityTransformTask` subclass). #2325 (ValidationRule), and historical asks for similar toggles, can all be solved by ~25-line additions following this pattern.
2. **`MappingStep.soql_filter` is mature**: per-step WHERE-clause filtering is now first-class, used by extract.py, the new declarative extract generator, and the hardcoded extract defaults. This closes #2505 cleanly and could be a reusable answer for any future "filter at extract time" requests.
3. **`hardcoded_default_declarations.py` quietly mitigates several historic data-shape bugs**: PricebookEntry filtering (#2951), sample-account exclusion, business hours, etc. Worth surfacing this file to triage doc readers — many "I extracted my org and it broke" issues are now invisibly handled here.
4. **Snowfakery has a working `get_debug_mode` integration; load/extract do not**: #2506 is half-complete. Wiring `get_debug_mode()` into `load.py`/`extract.py` and conditionally retaining tempdirs would close the gap with negligible risk.
5. **Rollback ≠ retry**: `enable_rollback` (added since 2021) is sometimes confused with the retry asked for in #2508. They are orthogonal: rollback undoes successful inserts on failure; retry would re-attempt failed records. Both have value.
6. **REST loader has caught up with Bulk on type coercion** (`process_bool_arg` is now used by `RestApiDmlOperation._record_to_json`); the empty-string→null fix (#3361) for upsert/update is also in place. Several "REST is stricter than Bulk" historic complaints are likely resolved by these two changes alone.

#### Scratch org aliases used

**None.** All 9 issues were classifiable from source-code reading and small in-process unit tests; no `cci org scratch` invocation was needed.

#### Repro test artifacts

-   `/tmp/repro/9/tests/test_2013_multistep.py` — confirms #2013 SQLAlchemy error
-   `/tmp/repro/9/tests/test_2096_rest_booleans.py` — confirms #2096 spec compliance (20/20)
-   `/tmp/repro/9/tests/test_3283_empty_date.py` — confirms #3283 fix in v4.10.0 (3/3)

All three test files run green against the v4.10.0 source via `uv run pytest <path>` from this worktree.

#### Deviations

None. No GitHub mutations. No git pushes. No edits under `cumulusci/robotframework/`. No edits inside main worktree at `/Users/jestevez/work/rel/CumulusCI`. No package additions to pyproject/lock.

#

-   **Theme**: bulkdata
-   **Worktree**: `.worktrees/repro-bulk-part2` @ `129238663` (= v4.10.0)
-   **Issues processed**: 9 / 9
-   **Scratch orgs provisioned**: 1 — `repro-bulk-p2-dev` (created 2026-05-14 09:48:57 UTC, username `test-9oxwkamse2zq@example.com`, Org Id `00DRt00000Q7HYE`). Provisioned during initial triage but ultimately not needed because all 9 issues turned out to be conclusive from code review and/or in-process unit tests against `cumulusci/tasks/bulkdata/`. Already cleaned up — see "Scratch org cleanup" section below.

#### Verdict tally

| Verdict                            | Count | Issues                                          |
| ---------------------------------- | ----: | ----------------------------------------------- |
| `REPRODUCED-on-v4.10.0`            |     7 | #3349, #3353, #3649, #3699, #3700, #3701, #3768 |
| `NOT-REPRODUCED-on-v4.10.0`        |     1 | #3360                                           |
| `INCONCLUSIVE-needs-flaky-network` |     1 | #3936                                           |
| `closed:duplicate-of-#NNNN`        |     0 | —                                               |

#### Pass-1 recommendations

| Recommendation               | Count | Issues                               |
| ---------------------------- | ----: | ------------------------------------ |
| `keep-open`                  |     5 | #3349, #3353, #3649, #3700, #3768    |
| `closed:stale-24mo`          |     2 | #3699, #3701                         |
| `closed:feature-implemented` |     1 | #3360                                |
| `unchanged`                  |     1 | #3936 (already maintainer kept-open) |

#### Bug vs feature breakdown

-   **Bugs** (4): #3349, #3700, #3768, #3936
    -   All four still present in v4.10.0 (with #3936 environment-dependent for the actual timeout, but the underlying missing-timeout-config gap is confirmed).
    -   2 are good-first-issue candidates (#3700 small fix; #3349 medium).
-   **Features** (5): #3353, #3360, #3649, #3699, #3701
    -   1 already implemented and should close: #3360 (`action: select`).
    -   1 small good-first-issue: #3649 (add `bulk_mode` option to `update_data`).
    -   1 active community ask: #3353 (cross-source recipe paths).
    -   2 low-priority with workarounds: #3699 (workaround via `soql_filter ORDER BY`), #3701 (related to #3699).

#### Cross-cutting findings

1. **`api_options={}` is hardcoded in multiple bulkdata tasks.** `update_data.py:184/211` is the case in #3649, but the same pattern appears in `extract.py:156`. A small refactor to make `api_options` (specifically `bulk_mode`) a first-class task option across all bulk tasks would resolve #3649 and similar friction.

2. **`MappingStep._get_required_permission_types` is too conservative for upserts.** #3700 is the master-detail variant; the same logic also affects formula fields (read-only) and other intentionally-non-updateable fields used as upsert lookups. A field-shape-aware permission check (using `cascadeDelete` / `relationshipName` / `nillable` from describe) would handle multiple field categories at once.

3. **RecordType-table naming derives from `sf_object` not `table` (#3349) and the same problem caused #2013 (Subagent 9).** Both bugs share a root cause: the code assumes a 1:1 mapping between `sf_object` and SQLite table within an extract run. A v5 refactor of mapping_parser to make the `table:` key the unambiguous primary key would fix both.

4. **Snowfakery `just_once` + `batch_size` (#3768) reflects a deliberate cleanup choice.** `_cleanup_object_tables` drops all object tables from the template before propagating it to subsequent batches, keeping only `_sf_ids`. To fix #3768, CCI needs to detect which objects are referenced via `random_reference`+`just_once` and preserve their rows in the template DB. This is non-trivial and intersects with the Snowfakery dev cutover (see master plan `snowfakery-coordination`).

5. **No timeout configuration anywhere (#3936).** `get_simple_salesforce_connection` and bulk-job polling never expose a timeout. For corporate-VPN users this manifests as `Read timed out. (read timeout=None)` from a server-side socket close. A v5 fix should add `org.timeout` config and read-timeout retry.

6. **`action: select` (added Aug 2024) resolves #3360 and likely overlaps several closed enhancement requests not in this bundle.** A grep of historical issues for "lookup existing records" / "reference existing data" might find more candidates to close.

#### Repro tests written (under `/tmp/repro/10/tests/`)

-   `test_3349_recordtype_table_collision.py` — proves `MappingStep` collides record-type table names for two steps sharing `sf_object`.
-   `test_3700_master_detail_upsert_perm.py` — proves `_check_field_permission` rejects MD lookup fields under UPSERT.

Both tests exercise `cumulusci.tasks.bulkdata.mapping_parser` only, no org needed, ~0.3s each.

#### Scratch org cleanup

`repro-bulk-p2-dev` was provisioned (see `scratch-info.log`) and has been confirmed cleaned up at the end of the session:

-   `uv run cci org list` shows no `repro-bulk-p2-*` entries.
-   `uv run cci org scratch_delete repro-bulk-p2-dev` returns `Org with name 'repro-bulk-p2-dev' does not exist.` (= already cleaned).
-   `sf data query --query "SELECT Id, ScratchOrg, SignupUsername FROM ActiveScratchOrg" --target-org CCIDevHub` returns one row whose username does NOT match `test-9oxwkamse2zq@example.com` — i.e. our scratch org is no longer active on the DevHub.
-   `sf org list --json` filtered for `repro-bulk-p2` / `test-9oxwkamse2zq` returns `[]`.

No `repro-bulk-p2-*` aliases or scratch orgs remain.

#### Deviations

None.

#

-   **Worktree**: `/Users/jestevez/work/rel/CumulusCI/.worktrees/repro-deps`
-   **HEAD SHA**: `12923866380211161c309f3afb55e67ef18a8890` (= v4.10.0 pin)
-   **Total processed**: 5 / 5
-   **Scratch orgs provisioned**: 0 (all issues resolved via Bucket A code-scan + unit-level repro)

#### Verdict tally

| Verdict                   | Count | Issues                     |
| ------------------------- | ----- | -------------------------- |
| REPRODUCED-on-v4.10.0     | 4     | #3603, #3604, #3619, #3886 |
| NOT-REPRODUCED-on-v4.10.0 | 1     | #3615                      |
| INCONCLUSIVE              | 0     | —                          |
| closed:duplicate-of-#NNNN | 0     | —                          |

Note: #3604 is a feature request; "REPRODUCED" here means the requested
capability is still missing in v4.10.0.

#### Recommended pass1 actions

| Recommendation                     | Issues                     |
| ---------------------------------- | -------------------------- |
| keep-open                          | #3603, #3604, #3619, #3886 |
| closed:not-reproducible-on-v4.10.0 | #3615                      |

#### Cross-cutting findings

1. **Dependency error messages are inconsistent**. `cumulusci/core/source/github.py`
   wraps repo-not-found and release-not-found cases in
   `DependencyResolutionError`, but lets ref-not-found leak as raw
   `github3.exceptions.NotFoundError` (`'404 [No message]'`). Similarly
   `resolvers.py:663`'s "Unable to resolve dependency" message names the dep
   but not the strategies tried. Both surface in #3603. A short follow-up
   ticket "wrap remaining github3 NotFoundError leaks in dependency code"
   would resolve this cleanly.

2. **Pin model is missing fields that are routine on dependencies**.
   `GitHubDependencyPin` (#3619) only carries `github`/`tag` — but a real
   pinned dep often needs `password_env_name`. The pin-resolution path
   (`pin.pin()`) also bypasses the password-propagation block in
   `resolve_dependency()`, so even when a dep declares the password, it gets
   silently dropped. Fix is small (add field, propagate in `pin.pin()`).

3. **Resolution-strategy alias names are confusing**. (#3615) `preproduction`
   sounds like "pre-prod = beta" but is in fact an alias for `latest_release`.
   This is a documentation/UX problem, not a code bug. Worth a cross-link in
   `docs/data.md` or release notes.

4. **Module-import-time log warnings produce noise on every cci run**.
   `select_utils` (#3886) emits at module import; because `extract.py` pulls
   it in transitively, the warning fires regardless of whether the user
   actually invokes `select` functionality. Common pattern fix: lazy-emit at
   first use of optional code path.

5. **None of these 5 issues required org access**. All were resolvable via
   targeted unit tests against in-process mocks. This generalizes the
   triage-cost estimate downward for future "dependencies" buckets.

#### Scratch org aliases used

None.

#### Cleanup

No scratch orgs were provisioned; no cleanup required.

#### Output files

-   `/tmp/repro/11/repro-results.csv`
-   `/tmp/repro/11/narrative.md`
-   `/tmp/repro/11/SUMMARY.md`
-   `/tmp/repro/11/tests/test_3603_404_messages.py` (4 tests, all passing)
-   `/tmp/repro/11/tests/test_3615_preproduction_strategy.py` (3 tests, all passing)
-   `/tmp/repro/11/tests/test_3619_pin_password.py` (4 tests, all passing)
-   `/tmp/repro/11/tests/test_3886_select_warning.py` (2 tests, all passing)

#### Deviations

None against bundle constraints. Two observations worth noting:

1. Mid-session, `git status -sb` briefly showed the branch label as
   `worktree/repro/bulk-part2`; by end-of-session it had updated to the
   expected `worktree/repro/deps`. The HEAD SHA was always `129238663`
   (= v4.10.0), so all repro evidence is valid against the intended source
   state.

2. `/tmp/repro/11/tests/` already contained 3 stale repro files from a prior
   subagent run (`test_3603_404_messaging.py`, `test_3619_pin_no_password.py`,
   `test_3886_select_optional_deps_warning.py`) that conflicted with my own
   tests by sharing module-level imports of `select_utils`. I deleted those
   stale files and re-ran my tests cleanly (13/13 passing). Other subagents'
   outputs in adjacent `/tmp/repro/<N>/` directories were not touched.

#### Final test verification

```
$ uv run pytest /tmp/repro/11/tests/ -v
======================== 13 passed, 1 warning in 0.35s =========================
```

#

Worktree: `/Users/jestevez/work/rel/CumulusCI/.worktrees/repro-ci-int` @ `129238663` (= v4.10.0)
Theme: `ci-integration` (mixed bucket — issues span Heroku/CI workflow, GitHub Actions, sfdx CLI integration)
Issues processed: 4 (all 4 in bundle-12.json)

#### Verdict tally

| Verdict                                       | Count | Issues       |
| --------------------------------------------- | ----: | ------------ |
| `REPRODUCED-on-v4.10.0`                       |     2 | #2153, #3471 |
| `NOT-REPRODUCED-on-v4.10.0`                   |     1 | #3479        |
| `INCONCLUSIVE-needs-cumulus-actions-workflow` |     1 | #3717        |
| **Total**                                     | **4** |              |

Bug vs feature breakdown:

-   1 feature (#2153) — REPRODUCED (still unimplemented)
-   3 bugs (#3471 REPRODUCED, #3479 NOT-REPRODUCED, #3717 INCONCLUSIVE)

#### Recommended pass1 actions

| Issue | Action                               | Reasoning                                                                                   |
| ----- | ------------------------------------ | ------------------------------------------------------------------------------------------- |
| #2153 | `keep-open`                          | Small, well-scoped enhancement to `MergeBranch._create_conflict_pull_request`; still wanted |
| #3471 | `keep-open`                          | Real bug; replace `compare.behind_by` at `merge.py:251` with a count of merged commits      |
| #3479 | `closed:not-reproducible-on-v4.10.0` | Root cause is user GHA shell expansion; cci already wraps the JSON parse error in v4.10.0   |
| #3717 | `unchanged`                          | Lives at cci ↔ cumulus-actions boundary; mirrors #3418 precedent                           |

#### Cross-cutting findings

1. **`MergeBranch` (`cumulusci/tasks/github/merge.py`) is the locus of two of the four issues** (#2153 and #3471). Both have small, well-localized fixes:

    - #2153: After `self.repo.create_pull(...)` in `_create_conflict_pull_request`, look up open PRs whose `head==branch_name` (the conflicted child branch) and post a comment linking back to the auto-generated conflict PR with resolution steps.
    - #3471: Replace `compare.behind_by` in the success log line with `len(list(compare.commits))` (or report the merge SHA returned by `self.repo.merge`). Add a unit test in `test_merge.py` that mocks a `compare` with `behind_by=0` but `files=[…]` to lock in the new behavior.

2. **cci has no GitHub Actions environment auto-detection.** `project_config.py::repo_info` only handles Heroku CI plus generic `CUMULUSCI_REPO_*` overrides. Repo-wide grep for `GITHUB_REF|GITHUB_HEAD_REF|GITHUB_SHA|GITHUB_ACTIONS` returns zero matches. This is the structural cause behind #3717 (and a contributing factor any time a `push`-triggered GHA job runs cci against a detached HEAD). Two viable directions, both out of scope for triage:

    - Fix in `cumulus-actions/standard-workflows`: set `CUMULUSCI_REPO_BRANCH` from `${{ github.head_ref || github.ref_name }}` and `CUMULUSCI_REPO_COMMIT` from `${{ github.sha }}` before invoking cci.
    - Add a `# GitHub Actions` block in `repo_info` parallel to the existing Heroku block.

3. **Stale 2023-era user-config issues with no reporter follow-up** (#3479) are good `closed:not-reproducible-on-v4.10.0` candidates when (a) the symptom is improved or wrapped in v4.10.0 and (b) the reviewer's clarifying question went unanswered for 2+ years. #3479 fits both criteria.

4. **Code stability for this theme is high.** Between the issue dates (2020-2023) and v4.10.0:
    - `cumulusci/tasks/github/merge.py` has had only refactors (ruff migration, `create_pull_request_on_conflict` option, `skip_future_releases` fixes) — no change to the `compare.behind_by` reporting line or to PR-creation behavior on conflict.
    - `cumulusci/core/config/sfdx_org_config.py` has had the JSON-error wrapper since 2020-11-24.
    - `cumulusci/core/config/project_config.py::repo_info` still only auto-detects Heroku.

#### Scratch org aliases used

**No scratch needed** — all 4 issues resolved by code-scan against the worktree (Bucket A). DevHub `CCIDevHub` was not touched.

#### Deviations from instructions

None. No GitHub mutations, no pushes, no edits under `cumulusci/robotframework/`, no work in the main worktree, no `pyproject.toml`/`uv.lock` changes, no scratch orgs provisioned.

#### Output files

-   `/tmp/repro/12/repro-results.csv`
-   `/tmp/repro/12/narrative.md`
-   `/tmp/repro/12/SUMMARY.md`

## Per-issue narratives

Concatenated from each subagent's `narrative.md`. Sorted by issue number. Headings normalized to `### #NNNN`.

<!-- subagent 7 -->

### #733: Prompt to delete scratch org when creating one that already exists

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```126:140:cumulusci/cli/runtime.py
    def check_org_overwrite(self, org_name):
        try:
            org = self.keychain.get_org(org_name)
            if org.scratch:
                if org.created:
                    raise click.ClickException(
                        f"Scratch org has already been created. Use `cci org scratch_delete {org_name}`"
                    )
            else:
                raise click.ClickException(
                    f"Org {org_name} already exists.  Use `cci org remove` to delete it."
                )
        except OrgNotFound:
            pass
        return True
```

Behaviour identical to the 2018 report — hard error, no interactive Y/N prompt.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 7-year-old `cli-usability` enhancement, no traction, original tracking W-028291.
-   pass2 labels: `enhancement,cli-usability,stale`

---

<!-- subagent 5 -->

### #808: deploy_packaging flow runs uninstall_packaged_incremental with wrong package name

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none (static analysis; live repro requires a real packaging org with a managed package whose name differs from `project__package__name`).

**Method**:
Read `cumulusci/tasks/salesforce/UninstallPackaged.py` and compared with `cumulusci/tasks/salesforce/install_package_version.py`.

**Evidence**:

-   `UninstallPackaged._init_options` (UninstallPackaged.py:22-25):

```22:25:cumulusci/tasks/salesforce/UninstallPackaged.py
    def _init_options(self, kwargs):
        super(UninstallPackaged, self)._init_options(kwargs)
        if "package" not in self.options:
            self.options["package"] = self.project_config.project__package__name
```

-   Compare to `InstallPackageVersion._init_options` (install_package_version.py:75-79) which DOES use the fall-back chain `name_managed -> name -> namespace`. The asymmetry is the bug.
-   Bug pattern is unchanged since 2018; no fix has landed.

**Recommended action**:

-   pass1: `keep-open` — small, contained fix.
-   pass2 labels: `bug`, `good-first-issue`

**Notes**: jlantz's 2018 follow-up about deprecating `project__package__name_managed` (legacy NPSP-only feature) is a separate, larger conversation; for this triage the minimal symmetric fix is enough.

---

<!-- subagent 7 -->

### #1348: Multiple Git Provider Support

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

`rg -li "gitlab" cumulusci/` and `rg -li "bitbucket" cumulusci/` both return zero matches. The `ci_feature` flow still hardcodes GitHub-specific tasks:

```767:789:cumulusci/cumulusci.yml
    ci_feature:
        group: Continuous Integration
        ...
        steps:
            0.5:
                task: github_parent_pr_notes
            ...
            5:
                task: github_automerge_feature
```

**Recommended action**:

-   pass1: `closed:stale-24mo` — large architectural change (multi-VCS abstraction); 6yr no traction; user `zenibako` confirmed using cci on GitLab via custom flows is feasible.
-   pass2 labels: `enhancement,stale,wontfix-candidate`

---

<!-- subagent 7 -->

### #1350: Unable to run tasks in remote projects

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: code-scan

**Evidence**:

The original `ModuleNotFoundError: No module named 'tasks'` is fixed via a synthetic `tasks` namespace package and per-source path extension:

```52:57:cumulusci/core/config/project_config.py
sys.modules.setdefault(
    "tasks", types.ModuleType("tasks", "Synthetic package for all repo tasks")
)
import tasks

tasks.__path__ = []
```

```657:679:cumulusci/core/config/project_config.py
            # If I can't load remote code, make sure that my
            # included repos can't either.
            if not self.allow_remote_code:
                spec.allow_remote_code = False
            else:
                project_config._add_tasks_directory_to_python_path()

        return project_config

    def _add_tasks_directory_to_python_path(self):
        # https://stackoverflow.com/a/2700924/113477
        if not self.allow_remote_code:
            return False

        directory = str(Path(self.repo_root) / "tasks")
        if directory not in tasks.__path__:
            self.logger.debug(f"Adding {directory} to tasks.__path__")
            tasks.__path__.append(directory)
```

The follow-up name-collision concern raised by `prescod` in 2022 (NPSP and EDA both registering `tasks.is_rd2_enabled`) is a **separate** issue from the original report.

**Recommended action**:

-   pass1: `closed:not-reproducible-on-v4.10.0` — original bug is fixed.
-   pass2 labels: `fixed`

---

<!-- subagent 7 -->

### #1432: CCI Inconsistencies in validating arguments

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: code-scan + unit test

**Evidence**:

Old-style `task_options` dict still does not validate unknown keys:

```186:196:cumulusci/core/tasks.py
    def _validate_options(self):
        missing_required = []
        for name, config in list(self.task_options.items()):
            if config.get("required") is True and name not in self.options:
                missing_required.append(name)

        if missing_required:
            required_opts = ",".join(missing_required)
            raise TaskOptionsError(
                f"{self.__class__.__name__} requires the options ({required_opts}) and no values were provided"
            )
```

Repro test passes (= unknown `colour` typo is silently accepted via YAML/Python path):

```
$ uv run pytest /tmp/repro/7/tests/test_1432_options_validation.py -q
.                                                                        [100%]
1 passed in 0.25s
```

Test path: `/tmp/repro/7/tests/test_1432_options_validation.py`.

**Mitigation**: Tasks that opted into the new Pydantic `Options` class (lines 159-184) now reject extras with `"extra options"`. So the bug is partially fixed for new-style tasks but persists for legacy ones.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 5yr; partial mitigation in place; full fix would require reworking every legacy `task_options` dict task.
-   pass2 labels: `bug,stale,partially-fixed`

---

<!-- subagent 9 -->

### #1769: Unusual case in test_load

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug (test code-smell)
**Org used**: none — code-only
**Method**: `git show` of the original 2020 commit referenced in the issue + grep of the current `test_load.py`.

**Evidence**:
The original line 352 in `158a2d4356f` (May 2020) was:

```python
lookups["Id"] = {"table": "accounts", "key_field": "sf_id"}
```

In v4.10.0 the same pattern survives, just wrapped in `MappingLookup`:

```736:739:cumulusci/tasks/bulkdata/tests/test_load.py
        lookups["Id"] = MappingLookup(name="Id", table="accounts", key_field="sf_id")
        lookups["Primary_Contact__c"] = MappingLookup(
            table="contacts", name="Primary_Contact__c"
        )
```

The pattern repeats at lines 754, 773, 801, 1119, 1187, 1255 — declaring `Id` as a "lookup" key inside the `lookups` dict so `_expand_mapping` can express the after-step's UPDATE-on-Id dependency. davidmreed acknowledged in 2020 it was "a horrible hack" he intended to clean up, but six years later it is still there, with zero downstream complaints.

**Recommended action**:

-   pass1: `closed:stale-24mo` — pure test-fixture nit; never escalated to a real bug; original commenters have moved on.
-   pass2 labels: `test-cleanup, low-priority`

---

<!-- subagent 9 -->

### #2013: Mapping files with steps that are not 1-1 with SObjects are unreliable for extraction

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none — code-only
**Method**: Direct unit test against `cumulusci.tasks.bulkdata.utils.create_table` with two `MappingStep` instances both named `Account`.

**Evidence**:
`create_table_if_needed` (`utils.py:133-139`) tries to detect duplicate tables but the SQLAlchemy `Table()` constructor raises first:

```133:139:cumulusci/tasks/bulkdata/utils.py
def create_table_if_needed(tablename, metadata, fields: T.List[Column]) -> Table:
    t = Table(tablename, metadata, *fields)
    inspector = inspect(metadata.bind)
    if inspector.has_table(tablename):
        raise BulkDataException(f"Table already exists: {tablename}")
    t.create(metadata.bind)
    return t
```

Reproduction (`/tmp/repro/9/tests/test_2013_multistep.py`) yields the exact 2020 traceback:

```
Exception type: InvalidRequestError
Exception message: Table 'Account' is already defined for this MetaData instance.
Specify 'extend_existing=True' to redefine options and columns on an existing
Table object.
```

**Recommended action**:

-   pass1: `keep-open` — bug is real, easy to reproduce, easy to fix (catch the SQLAlchemy error and re-raise as `BulkDataException`, or validate at mapping-parse time).
-   pass2 labels: `bug, bulkdata, extract_dataset, error-handling`

---

<!-- subagent 9 -->

### #2096: REST dataloads throw errors that Bulk loads do not

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none — code-only
**Method**: Inspect `RestApiDmlOperation._record_to_json` and `process_bool_arg`; parametric unit test against the full Data Loader spectrum.

**Evidence**:
REST DML pre-converts boolean columns:

```778:784:cumulusci/tasks/bulkdata/step.py
    def _record_to_json(self, rec):
        result = dict(zip(self.fields, rec))
        for boolean_field in self.boolean_fields:
            try:
                result[boolean_field] = process_bool_arg(result[boolean_field] or False)
            except TypeError as e:
                raise BulkDataException(e)
```

`process_bool_arg` (`core/utils.py:75-83`) accepts the entire spectrum from the Data Loader guide cited in the issue (yes/y/true/on/1 → True; no/n/false/off/0 → False; case-insensitive). Test `/tmp/repro/9/tests/test_2096_rest_booleans.py` confirms 20/20 spectrum values pass.

**Recommended action**:

-   pass1: `closed:not-reproducible-on-v4.10.0`
-   pass2 labels: `resolved, bulkdata`

---

<!-- subagent 7 -->

### #2140: Prompt Org Configs when Org Does Not Exist and Command Runs Against It

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```95:104:cumulusci/cli/runtime.py
    def get_org(self, org_name=None, fail_if_missing=True):
        if org_name:
            org_config = self.keychain.get_org(org_name)
        else:
            org_name, org_config = self.keychain.get_default_org()
        if org_config:
            org_config = self.check_org_expired(org_name, org_config)
        elif fail_if_missing:
            raise click.UsageError("No org specified and no default org set.")
        return org_name, org_config
```

`keychain.get_org` raises `OrgNotFound` -> `cli/org.py:530-531` shows `"Org {name} does not exist in the keychain"`. No interactive prompt offering available scratch configs.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 5yr `cli-usability` enhancement with no traction.
-   pass2 labels: `enhancement,cli-usability,stale`

---

<!-- subagent 12 -->

### #2153: Add comment to original PR which tags all branch subscribers when a merge

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: Bucket A — code-scan against `cumulusci/tasks/github/merge.py` and grep for `create_comment` / `issue_comment` across `cumulusci/tasks/github`.

**Evidence**:

`cumulusci/tasks/github/merge.py` `_create_conflict_pull_request` (the only place an auto-merge PR is created):

```264:288:cumulusci/tasks/github/merge.py
    def _create_conflict_pull_request(self, branch_name, source):
        """Attempt to create a pull request from source into branch_name if merge operation encounters a conflict"""
        if branch_name in self._get_existing_prs(
            self.options["source_branch"], self.options["branch_prefix"]
        ):
            self.logger.info(
                f"Merge conflict on branch {branch_name}: merge PR already exists"
            )
            return

        try:
            pull = self.repo.create_pull(
                title=f"Merge {source} into {branch_name}",
                base=branch_name,
                head=source,
                body="This pull request was automatically generated because "
                "an automated merge hit a merge conflict",
            )
            self.logger.info(
                f"Merge conflict on branch {branch_name}: created pull request #{pull.number}"
            )
        except github3.exceptions.UnprocessableEntity as e:
            self.logger.error(
                f"Error creating merge conflict pull request to merge {source} into {branch_name}:\n{e.response.text}"
            )
```

The method only creates the conflict PR; it never opens a comment on any PR (the original child PR or otherwise). Repo-wide grep for `create_comment|issue_comment|pr.create_comment|comment.*pull_request` under `cumulusci/tasks/github` returns no hits in production code (only test fixtures). Davis Agli's response in the thread agreed with the issue reporter that the appropriate place would be a comment on the original PR. Feature is unimplemented in v4.10.0.

**Recommended action**:

-   pass1: `keep-open` — small, well-scoped enhancement; reasonable "good-second-issue".
-   pass2 labels: `enhancement, github, merge-conflict`

---

<!-- subagent 9 -->

### #2325: Task to turn off validation rules to allow data insert

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Org used**: none — code-only
**Method**: Grep cumulusci.yml + `cci task list` for any `validation_rule` / `disable_*` task.

**Evidence**:

-   Trigger analog: `disable_tdtm_trigger_handlers` / `restore_tdtm_trigger_handlers` (`cumulusci.yml:738-747`).
-   DuplicateRule analog: `set_duplicate_rule_status` → `cumulusci.tasks.metadata_etl.duplicate_rules.SetDuplicateRuleStatus` (a 25-line `MetadataSingleEntityTransformTask` subclass with `entity = "DuplicateRule"`).
-   ValidationRule equivalent: **none.** `cci task list | grep -i -E "validation|rule"` returns only `set_duplicate_rule_status`.

The pattern to copy is trivially established. The user's specific use case (relative-date hearings during dataset insert) is exactly what `disable_tdtm_trigger_handlers` solves for triggers; ValidationRule needs the same.

**Recommended action**:

-   pass1: `keep-open` — feature still missing, clear implementation pattern, modest scope.
-   pass2 labels: `enhancement, bulkdata, metadata_etl, good-first-issue`

---

<!-- subagent 7 -->

### #2402: Create a --rebuild-org parameter for cci flow run

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```119:145:cumulusci/cli/flow.py
@flow.command(name="run", help="Runs a flow")
@click.argument("flow_name")
@click.option("--org", help="Specify the target org.  By default, runs against the current default org")
@click.option("--delete-org", is_flag=True, help="If set, deletes the scratch org after the flow completes")
@click.option("--debug", is_flag=True, help="Drops into pdb, the Python debugger, on an exception")
@click.option("-o", nargs=2, multiple=True, help="...")
@click.option("--no-prompt", is_flag=True, help="...")
@pass_runtime(require_keychain=True)
def flow_run(runtime, flow_name, org, delete_org, debug, o, no_prompt):
```

Only `--delete-org` exists. `rg -i "rebuild.org"` returns zero hits.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 5yr; tracked W-10502624 (no movement); user can accomplish via `cci org scratch_delete X && cci flow run`.
-   pass2 labels: `enhancement,stale`

---

<!-- subagent 9 -->

### #2505: Filtering records to be extracted

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: feature
**Org used**: none — code-only
**Method**: Grep `mapping_parser.py` and `extract.py` for `soql_filter` / WHERE-clause support.

**Evidence**:
Per-step SOQL filter is now first-class:

```120:120:cumulusci/tasks/bulkdata/mapping_parser.py
    soql_filter: Optional[str] = None  # soql_filter property
```

```142:147:cumulusci/tasks/bulkdata/extract.py
        if mapping.soql_filter is not None:
            soql = self.append_filter_clause(
                soql=soql, filter_clause=mapping.soql_filter
            )
```

The new extract-mapping generator wires user-declared `where:` into `soql_filter` (`extract_mapping_file_generator.py:26`), and the existing hardcoded extract declarations (`extract_dataset_utils/hardcoded_default_declarations.py`) already use this for per-sObject filtering. Tests exercise the plain filter, the WHERE-prefixed variant, and combinations with record_type (`test_extract.py:1216, 1248, 1280`).

**Recommended action**:

-   pass1: `closed:feature-implemented`
-   pass2 labels: `resolved, bulkdata, extract_dataset`

---

<!-- subagent 9 -->

### #2506: Bulk Operations should have a --debug mode which maintains logs and tempfiles

**Verdict**: REPRODUCED-on-v4.10.0 (partial)
**Repro type**: feature
**Org used**: none — code-only
**Method**: Grep all bulkdata modules for `get_debug_mode` / `delete=False` / `TemporaryDirectory` usage.

**Evidence**:

-   Snowfakery task (`snowfakery.py:241,355,385,565`) calls `get_debug_mode()` and at `:386` logs `f"Working Directory: {tempdir}"` per loop iteration.
-   `extract.py`, `step.py` — **zero** references to `debug_mode` or `get_debug_mode`.
-   `load.py:283` uses `tempfile.TemporaryFile` with no debug-mode override; the file is auto-deleted on context exit regardless of debug.

So the ask is half-met: Snowfakery cooperates with debug mode; the workhorse `load_dataset` / `extract_dataset` tasks do not.

**Recommended action**:

-   pass1: `keep-open` — partial implementation; remaining work is straightforward (wire `get_debug_mode()` into load/extract, conditionally use `TemporaryDirectory(delete=False)` and emit path).
-   pass2 labels: `enhancement, bulkdata, extract_dataset, load_dataset, debugging`

---

<!-- subagent 7 -->

### #2507: Undo mode for CumulusCI Insert

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

No `undo_insert` task exists (`rg -l undo_insert` returns nothing). Closest functionality is `enable_rollback` on `load_dataset` and `snowfakery` tasks:

```97:99:cumulusci/tasks/bulkdata/load.py
        "enable_rollback": {
            "description": "When True, performs rollback operation incase of error. Defaults to False"
        },
```

That only triggers rollback on error during the load; it does not provide the post-hoc "delete everything we ever inserted" capability the requester described.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr feature with partial mitigation already shipped.
-   pass2 labels: `enhancement,stale,partially-fixed`

---

<!-- subagent 9 -->

### #2508: Manual load retries

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Org used**: none — code-only
**Method**: `cci task list | grep -i retry` and grep load.py for retry/failed-record persistence.

**Evidence**:

-   `cci task list` returns no retry-named task.
-   `load.py` has an `enable_rollback` option (`:97-98`, `RollbackType` enum at `:1051`) but rollback **undoes successful inserts when failures occur** — the opposite of "retry the failures."
-   `RowErrorChecker` (`utils.py:158`) only logs and optionally raises; it does not persist a failed-rows artifact that could be replayed.

**Recommended action**:

-   pass1: `keep-open` — distinct from rollback; would need (a) failed-row CSV/SQL persistence + (b) a new `retry_failed_load` task that consumes it.
-   pass2 labels: `enhancement, bulkdata, load_dataset, reliability`

---

<!-- subagent 7 -->

### #2697: 'namespaced' field stale in `cci org info` after switching org def

**Verdict**: INCONCLUSIVE-needs-scratch-slot
**Repro type**: bug
**Method**: code-scan (no scratch provisioned)

**Evidence**:

The cci `namespaced` field is set from the cci YAML config, not derived from the SFDX scratch def file:

```57:75:cumulusci/core/keychain/base_project_keychain.py
    def create_scratch_org(
        self, org_name, config_name, days=None, set_password=True, release=None
    ):
        """Adds/Updates a scratch org config to the keychain from a named config"""
        scratch_config = self.project_config.lookup(f"orgs__scratch__{config_name}")
        ...
        scratch_config["scratch"] = True
        scratch_config.setdefault("namespaced", False)
```

This means `cci org info` reflects the cci `orgs__scratch__qa.namespaced` value, not whatever the SFDX `qa.json` says. Since the user changed only the SFDX `qa.json` (not the cci YAML), cci's view of `namespaced` is unchanged. This is **likely working as designed** but conflicts with the user's mental model.

I did not provision a scratch org to confirm because (a) the code reading is unambiguous and (b) DevHub-slot conservation. Marking inconclusive only because final verification of the `cci org info` output panel was not exercised live.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 5yr stale; design/docs friction rather than a defect; request more info if reopened.
-   pass2 labels: `bug,stale,needs-info`

---

<!-- subagent 5 -->

### #2826: deploy_unmanaged flow is supposed to silently do nothing if there's not actually a package directory

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug (enhancement-flavored)
**Org used**: none (purely local task)

**Method**:
Inspected `cumulusci/tasks/metadata/package.py`:

-   `PackageXmlGenerator.parse_types` (line 107) calls `os.listdir(self.directory)` without checking existence.
-   `UpdatePackageXml._init_task` (line 590) and `_run_task` (line 612) do not guard for missing path.

Wrote a unit-level repro at `/tmp/repro/5/tests/issue-2826/repro_unit.py` that instantiates `UpdatePackageXml` against a temp dir containing no `src/`. Result: raises `FileNotFoundError: [Errno 2] No such file or directory: '/var/.../src'`. Bug present.

**Recommended action**:

-   pass1: `keep-open` — small, contained fix.
-   pass2 labels: `bug`, `good-first-issue`

**Notes**: Could be fixed at the task layer (skip with logger.info when path missing) or at the flow layer (`when:` guard on the deploy_unmanaged steps). Task-layer is more defensible because the same task may be referenced from custom flows.

---

<!-- subagent 9 -->

### #2951: Error in task load_dataset - Standard_price_not_defined

**Verdict**: REPRODUCED-on-v4.10.0 (with mitigation)
**Repro type**: bug
**Org used**: none — code-only
**Method**: Grep load.py / step.py for any PricebookEntry-specific sequencing logic; inspect `hardcoded_default_declarations.py`.

**Evidence**:
No special handling exists in the loader to sequence Standard-Price-Book PricebookEntries before custom-pricebook PricebookEntries within a single mapping step. Within one Bulk job, records are processed in parallel within batches and Salesforce throws `STANDARD_PRICE_NOT_DEFINED` when a custom price is created before the matching standard price.

Mitigation already in place for the `extract_dataset` → `load_dataset` round-trip:

```14:18:cumulusci/tasks/bulkdata/extract_dataset_utils/hardcoded_default_declarations.py
    ExtractDeclaration(
        sf_object="PricebookEntry",
        where="Pricebook2.Id != NULL and Pricebook2.Name != 'Standard Price Book'",
    ),
    ExtractDeclaration(sf_object="Pricebook2", where="Name != 'Standard Price Book'"),
```

So default extracts skip the Standard Price Book entirely, and the typical flow doesn't hit the bug. But the reporter built a mapping by hand that included both, and that path is still broken.

**Recommended action**:

-   pass1: `keep-open` — bug is latent. Fix options: (a) loader auto-splits PricebookEntry into two implicit batches (standard pricebook first); (b) document the requirement and validate at parse time that PricebookEntry steps are not "mixed."
-   pass2 labels: `bug, bulkdata, load_dataset, pricebook, documentation`

---

<!-- subagent 1 -->

### #2979: deploy task should deploy from default entry in packageDirectories

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Inspected the `deploy` task definition in `cumulusci/cumulusci.yml` and the `default_package_path` helper in `cumulusci/core/config/project_config.py`. Searched for `default_package_path` usages across the codebase to see whether any deploy/Deploy task consumes it.

**Evidence**:

-   `cumulusci/cumulusci.yml:227-229` — the `deploy` task still hard-codes `path: src` for `cumulusci.tasks.salesforce.Deploy`.
-   `cumulusci/core/config/project_config.py:517-525` — `default_package_path` correctly reads `packageDirectories[*].default` from `sfdx-project.json` when `project__source_format == "sfdx"`.
-   The only consumer of `default_package_path` is `cumulusci/tasks/create_package_version.py:230`. The Deploy task does not consult it.

**Recommended action**:

-   pass1: `keep-open` — feature still missing; davisagli's 2021 design comment (3-tier fallback `path` -> sfdx default -> `src`) remains the natural plan.
-   pass2 labels: `severity:low,area:packaging,area:sfdx,state:needs-design`

---

<!-- subagent 7 -->

### #3015: Remove imported dx org from cci list without deleting actual scratch

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```519:543:cumulusci/cli/org.py
@org.command(name="remove", help="Removes an org from the keychain")
@orgname_option_or_argument(required=True)
@click.option("--global-org", is_flag=True, help="...")
@pass_runtime(require_project=False, require_keychain=True)
def org_remove(runtime, org_name, global_org):
    try:
        org_config = runtime.keychain.get_org(org_name)
    except OrgNotFound:
        raise click.ClickException(f"Org {org_name} does not exist in the keychain")

    if org_config.can_delete():
        click.echo("A scratch org was already created, attempting to delete...")
        try:
            org_config.delete_org()
        ...
    runtime.keychain.remove_org(org_name, global_org)
```

No `--keep-org` flag. davisagli's manual workaround (delete `~/.cumulusci/<project>/<org>.org` directly) still applies.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr; tracked W-10502512.
-   pass2 labels: `enhancement,stale`

---

<!-- subagent 7 -->

### #3024: Order of flow groups in `cumulusci/cumulusci.yml`

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

Sequence of unique `group:` values in `cumulusci/cumulusci.yml` (first appearance):

```
Metadata Transformations
Salesforce Users
Salesforce
Salesforce Preflight Checks
Utilities
Data Operations
Salesforce Communities
Setup
Salesforce Packages
Salesforce Metadata
Marketing Cloud
OmniStudio
Salesforce DX
GitHub
Release Operations
Push Upgrades
Salesforce Bulk API
Robot Framework
NPSP/EDA
Continuous Integration
Post-Install Configuration
Dependency Management
```

`Continuous Integration` is buried near the bottom; `Org Setup` (the user's preferred name) does not exist (uses `Setup`); ordering does not match the user's request.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr cosmetic VS Code extension request; the true fix is sorting at the consumer (the extension) rather than rearranging the canonical YAML.
-   pass2 labels: `enhancement,stale`

---

<!-- subagent 2 -->

### #3137: cci task run update_package_xml and Salesforce Case Custom Object

**Verdict**: REPRODUCED-on-v4.10.0 (treated as feature request)
**Repro type**: feature

**Method**:
Inspected `cumulusci/tasks/metadata/package.py` `CustomObjectParser` (lines
443–482). It explicitly skips any object file that doesn't end in `__c`,
`__mdt`, `__e`, or `__b`. Inspected `UpdatePackageXml` task_options
(package.py:563–584) — no opt-in option such as `include_standard_objects`.
The maintainer's response on the issue agreed the behavior is by-design
(holdover from managed-package world) and committed only to "investigate";
no design has landed.

**Evidence**:

-   `cumulusci/tasks/metadata/package.py:451-458` skips standard objects.
-   `cumulusci/tasks/metadata/package.py:562-584` `UpdatePackageXml.task_options`
    has only `path`, `output`, `package_name`, `managed`, `delete`,
    `install_class`, `uninstall_class`.

**Recommended action**:

-   pass1: keep-open — a real product gap remains; mark for design discussion.
-   pass2 labels: `severity:low,area:metadata-etl,type:enhancement,state:needs-design`

---

<!-- subagent 7 -->

### #3161: Ability to Hide Option Values When Using Task Options

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```300:320:cumulusci/core/flowrunner.py
    def _log_options(self, task: "BaseTask"):
        ...
        for key, info in task.task_options.items():
            value = task.options.get(key)
            if value is not None:
                if type(value) is not list:
                    value = self._obfuscate_if_sensitive(value, info)
                    task.logger.info(f"  {key}: {value}")
                ...

    def _obfuscate_if_sensitive(self, value: str, info: dict) -> str:
        if info.get("sensitive"):
            value = 8 * "*"
        return value
```

A masking infrastructure was added (task-option metadata can opt in via `sensitive: True`), but:

1. The Robot `vars` option is not marked sensitive (`cumulusci/tasks/robotframework/robotframework.py:54-56`).
2. There's no CLI/Robot-side flag for the user to mark an ad-hoc `-o` value as sensitive.

So the user's specific request (mask multi-line GitHub Actions secrets passed via `-o robot__vars …`) is **partially mitigated** but not fully solved.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr; partial fix in place.
-   pass2 labels: `enhancement,stale,partially-implemented`

---

<!-- subagent 5 -->

### #3165: Update Admin Profile task fails when specifying record types without custom package.xml

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none for the unit repro; live test would need a Case "Case" record type in the scratch org

**Method**:
Read `cumulusci/tasks/salesforce/update_profile.py` carefully:

-   `_generate_package_xml(RETRIEVE)` calls `_expand_package_xml(package_xml)` only when `include_packaged_objects=True` (line 137-138).
-   `_expand_package_xml` calls `_expand_package_xml_objects(package_xml)` (line 182).
-   `_expand_package_xml_objects` (line 184-201) is what walks `record_types` and inserts each referenced object into `<types name="CustomObject">/<members>`.
-   Therefore: when `include_packaged_objects` is False (the default unless `minimum_cumulusci_version >= 3.9.0`), record_types referencing objects not in the default `cumulusci/files/admin_profile.xml` (e.g. `Case`) never get added.
-   Confirmed by the existing test `test_init_options__include_packaged_objects` (test_ProfileGrantAllAccess.py:609-615) which explicitly asserts `task._expand_package_xml.assert_not_called()` in the False branch.

Wrote `/tmp/repro/5/tests/issue-3165/repro_unit.py`. Output (key parts):

```
include_packaged_objects = False
--- generated package.xml ---
<?xml version="1.0" encoding="UTF-8"?>
<Package xmlns="http://soap.sforce.com/2006/04/metadata">
    <types>
        <members>*</members>
        <members>Account</members>
        <members>Campaign</members>
        ...
        <members>Opportunity</members>
        <name>CustomObject</name>
    </types>
    ...
</Package>
--- end ---
REPRODUCED: 'Case' is NOT in CustomObject members.
```

**Recommended action**:

-   pass1: `keep-open` — single-line refactor.
-   pass2 labels: `bug`

**Notes**: Smallest fix at update_profile.py:137 — always call `self._expand_package_xml_objects(package_xml)` regardless of `include_packaged_objects`, and only call the broader `self._expand_package_xml` (which does the Tooling API query) when `include_packaged_objects=True`. `_expand_package_xml_objects` itself only walks the user-supplied options, no API call.

---

<!-- subagent 5 -->

### #3167: Add ability to define page layout assignments with record types using the update_admin_profile task

**Verdict**: NOT-REPRODUCED-on-v4.10.0 (feature implemented)
**Repro type**: feature
**Org used**: none

**Method**:
Read `cumulusci/tasks/salesforce/update_profile.py`:

-   `task_options['record_types']` description (lines 32-34) explicitly documents the `page_layout` key.
-   `_set_record_types` lines 280-298 handle `page_layout`: locate any existing `<layoutAssignments>` matching the record type and update its `<layout>`, or append a new `<layoutAssignments>` block.

`git log -S "page_layout" -- cumulusci/tasks/salesforce/update_profile.py` shows the feature landed in commit `f2ff04bd5` (PR #3243 by davidmreed, merged 2022-06-16) — well before v4.10.0.

**Recommended action**:

-   pass1: `close-as-implemented` with reference to PR #3243.
-   pass2 labels: `enhancement`

**Notes**: Could also add a small docs example.

---

<!-- subagent 9 -->

### #3283: json parser error when empty string passed for date field during upsert or update

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none — code-only
**Method**: Verify PR #3361 (commit `b0bfb70e0`) is in `129238663` via `git merge-base --is-ancestor`; small unit test against `RestApiDmlOperation._record_to_json` for UPDATE/UPSERT/INSERT operations.

**Evidence**:
Fix is in place at `step.py:795-796`:

```789:797:cumulusci/tasks/bulkdata/step.py
        if self.operation is DataOperationType.INSERT:
            result = {
                k: result[k]
                for k in result
                if result[k] is not None and result[k] != ""
            }
        elif self.operation in (DataOperationType.UPDATE, DataOperationType.UPSERT):
            result = {k: (result[k] if result[k] != "" else None) for k in result}
```

Repro test (`/tmp/repro/9/tests/test_3283_empty_date.py`) verifies: empty `Birthdate` becomes JSON null on UPDATE and UPSERT (no longer triggering JSON_PARSER_ERROR), and is omitted entirely for INSERT. The reporter's own final comment ("Fixed in #3361") aligns.

**Recommended action**:

-   pass1: `closed:fixed-by-pr-#3361`
-   pass2 labels: `resolved, bulkdata, load_dataset`

<!-- subagent 7 -->

### #3307: Project Template Support for `cci project init`

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

`rg "template" cumulusci/cli/project.py` only finds references to internal Jinja templates rendered from `cumulusci/files/templates/project` (lines 220-329). No `--template` CLI option exists. `project_init` (line 41) takes no template-source argument.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr; explicitly described by the requester as "low priority / nice to have".
-   pass2 labels: `enhancement,stale`

---

<!-- subagent 2 -->

### #3320: Metadata ETL task to Deactivate a Flow

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Greped for `[Dd]eactivate.*[Ff]low|DeactivateFlow|deactivate_flow` across the
codebase and inspected `cumulusci/cumulusci.yml`.

**Evidence**:

-   `cumulusci/cumulusci.yml:10-15` ships a `deactivate_flow` task that
    reuses `cumulusci.tasks.salesforce.activate_flow.ActivateFlow` with
    `status: False`.
-   `cumulusci/tasks/salesforce/activate_flow.py:33-65` toggles
    `activeVersionNumber` to 0 when `status` is falsy, i.e. real deactivation.

**Recommended action**:

-   pass1: closed:feature-implemented — `cci task run deactivate_flow` is
    shipped; reporter likely missed it.
-   pass2 labels: `area:metadata-etl,type:enhancement,resolution:already-implemented`

---

<!-- subagent 2 -->

### #3331: Task update_package_xml does not write correct package.xml for AssignmentRules

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/tasks/metadata/metadata_map.yml` and wrote two tests: one
that asserts the YAML mapping is correct, one that runs `PackageXmlGenerator`
on a sample `assignmentRules/Case.assignmentRules` fixture and asserts the
emitted `<name>` element is `AssignmentRules` (plural).

**Evidence**:

-   `cumulusci/tasks/metadata/metadata_map.yml:45-48` maps the
    `assignmentRules` folder to `type: AssignmentRule` (singular). MDAPI
    expects the plural type name (cf. `autoResponseRules:` at lines 60-63
    which is already correctly `AutoResponseRules`).
-   Test output: both `test_issue_3331_*` tests fail; observed
    `<name>AssignmentRule</name>` instead of `<name>AssignmentRules</name>`.

**Recommended action**:

-   pass1: keep-open — one-line YAML fix; reporter offered a PR.
-   pass2 labels: `severity:medium,area:metadata-etl,type:bug,good-first-issue`

---

<!-- subagent 6 -->

### #3347: Cannot release an unlocked beta package with `release_unlocked_beta`

**Verdict:** `NOT-REPRODUCED-on-v4.10.0`

### Original symptom

User on CumulusCI 3.64.0 (2022-08) ran `cci flow run release_unlocked_beta` and the first task `create_package_version` died with a confusing low-level error:

```
TypeError: expected str, bytes or os.PathLike object, not NoneType
  at create_package_version.py line 377:
    with open(self.org_config.config_file, "r") as f:
```

Root cause: `org_config.config_file` is `None` for persistent orgs (DevHub, Developer Edition, etc.), but the user (likely) ran the flow against the DevHub directly. `release_unlocked_beta` requires a scratch target org; the old code fell through with an opaque error.

### Evidence on v4.10.0

`cumulusci/tasks/create_package_version.py` lines 44–46 and 158–159:

```44:46:cumulusci/tasks/create_package_version.py
PERSISTENT_ORG_ERROR = """
Target org scratch org definition file missing. Persistent orgs like a Dev Hub can't be used for 2GP package uploads.
"""
```

```158:159:cumulusci/tasks/create_package_version.py
        if not self.org_config.config_file:
            raise TaskOptionsError(PERSISTENT_ORG_ERROR)
```

The early `_init_options` check raises a clear `TaskOptionsError` before any `open()` is attempted. Fix landed in commit `2a9cadcb1` on 2023-10-12 (`added_clear_error`), refined in `8f62d3153` and `8328bfb9d`.

### Test verification

```text
$ uv run pytest "cumulusci/tasks/tests/test_create_package_version.py::TestPackageConfig::test_org_config" -x
1 passed in 0.22s
```

The test (`test_create_package_version.py:159–167`) explicitly sets `org_config.config_file = None` and asserts that `CreatePackageVersion` raises `TaskOptionsError` matching `PERSISTENT_ORG_ERROR`.

### Recommendation

-   **Pass 1:** close-with-comment ("Fixed by commit `2a9cadcb1` (PR adding clear error message). v4.10.0 raises a clear `TaskOptionsError` directing users to use a scratch org target.")
-   **Pass 2 label:** `resolved-by-clear-error-message`
-   The underlying limitation — cannot use a persistent (DevHub) org as the target for 2GP package upload — is preserved by design and now communicated clearly.

---

<!-- subagent 10 -->

### #3349: Make generated dataset recordType tables unique based on table instead of sf_object

**Verdict:** `REPRODUCED-on-v4.10.0` — bug, structural

`MappingStep.get_source_record_type_table()` and `get_destination_record_type_table()` in `cumulusci/tasks/bulkdata/mapping_parser.py:177-179` build the SQLite table name solely from `self.sf_object` (`f"{self.sf_object}_rt_mapping"` and `f"{self.sf_object}_rt_target_mapping"`). Two mapping steps targeting the same `sf_object` (the canonical case is `Account` Person vs Business with different `record_type:` values) thus produce the same table name. `load.py:552` and `extract.py:259/393` both use those names without per-step disambiguation.

Repro test (`/tmp/repro/10/tests/test_3349_recordtype_table_collision.py`) constructs two `MappingStep` objects with `sf_object="Account"` and different `record_type` values and asserts that both source and target table names collide — assertion passes, confirming the bug.

The maintainer label `wi-created` (W-11466074) is present, so this is exempt from the stale-24mo close. **Recommended pass1: `keep-open`.** Suggested fix: include `self.table` (or a hash of `record_type`+`filter`) in the generated table name when more than one mapping step shares an `sf_object`.

<!-- subagent 10 -->

### #3353: Enable Snowfakery task to use recipes from other repositories

**Verdict:** `REPRODUCED-on-v4.10.0` — feature still unimplemented

`Snowfakery._validate_options` in `cumulusci/tasks/bulkdata/snowfakery.py:159-162` validates the `recipe` option via `Path(recipe).exists()` only. There is no `SOURCE_NAME:path` parsing, and no call to `project_config.sources` / `project_config.get_source(...)` anywhere in `snowfakery.py`. The recipe string is passed straight to Snowfakery as a filesystem path.

This is a documented community ask (resurfaced in 2024-08 by `davidjray` and `jnesong`), not just a single reporter. Workaround today is `cci org import` from inside the source repository.

**Recommended pass1: `keep-open`.** Suggested fix: pre-process the `recipe` option to detect a `SOURCE_NAME:path` prefix and resolve it via `project_config.get_source(name).fetch().path` before existence check.

<!-- subagent 10 -->

### #3360: Read Only Object Lookup for Load_Dataset

**Verdict:** `NOT-REPRODUCED-on-v4.10.0` — feature implemented

The `action: select` mapping step (added by commit `b15945203`, "Core Logic for Selecting Records from Target Org", 2024-08-19, well before v4.10.0) provides exactly this behavior. It is fully wired through `cumulusci/tasks/bulkdata/select_utils.py`, the `SELECT` branch in `step.py`, and the `mapping_select.yml` test fixture. `select_options.strategy` (`similarity`, etc.), `select_options.filter`, and `select_options.priority_fields` allow the user to populate a lookup table from existing org records without DML, which is precisely the "read-only" semantic the issue requested.

**Recommended pass1: `closed:feature-implemented`.** Close-comment should cite the SELECT action and `mapping_select.yml`.

<!-- subagent 3 -->

### #3418: Error creating 1gp release

**Verdict**: INCONCLUSIVE-needs-cumulus-actions-workflow
**Repro type**: bug
**Org used**: none (no cci code path under test)

**Method**:
Read the cci docs and source for any code that would invoke `auth:sfdxurl:store` or otherwise parse the `PACKAGING_ORG_AUTH_URL` secret. The error message in the issue is verbatim text from the sfdx CLI (`auth:sfdxurl:store`), invoked by the `SFDO-Community/standard-workflows/.github/workflows/production-1gp.yml` workflow before cci ever runs. Searched the repo for `sfdxurl|SFDX_AUTH_URL|PACKAGING_ORG_AUTH_URL` — only hit is `docs/github-actions.md` (documentation pointing users at the standard-workflows repo).

**Evidence**:

-   `docs/github-actions.md:101-119` — examples reference `SFDO-Community/standard-workflows/.github/workflows/{beta,production}-1gp.yml@main` and the `packaging-org-auth-url` secret.
-   No occurrence of `auth:sfdxurl:store` anywhere in the cci tree.
-   davidmreed's 2022 comment on the issue: "I believe I know the issue here and I will seek to address it this evening" — implies the fix landed in the third-party workflow, not in cci.
-   Issue is still OPEN on GitHub but no `closedByPullRequestsReferences`.

**Recommended action**:

-   pass1: `unchanged` — keep open until we can confirm whether SFDO-Community fix is in place; transfer or cross-link there if appropriate.
-   pass2 labels: `needs-info`, `needs-repro`

---

<!-- subagent 1 -->

### #3429: Support overriding `cumulusci.yml` to be used for configuration

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Searched for `CUMULUSCI_YML`, `CUMULUSCI_EXTRA_YAML`, `extra_yaml`, `--extra-yaml`, `--configFile` across the v4.10.0 source. Inspected `BaseProjectConfig.__init__` and `_load_config` to see how YAML is layered. Verified the `extra-yaml-cli-flag` branch is NOT an ancestor of HEAD.

**Evidence**:

-   `cumulusci/core/config/project_config.py:82` — `config_filename = "cumulusci.yml"` is hardcoded.
-   `cumulusci/core/config/project_config.py:118-184` — only an `additional_yaml` kwarg (programmatic, used by MetaCI) is supported; no env var or CLI plumbing.
-   `git merge-base --is-ancestor 9d650ace2 HEAD` returns non-zero — PR #3969 (commits prefixed `feat(cli): add resolve_extra_yaml helper for --extra-yaml flag`) is in flight on branch `extra-yaml-cli-flag` but not merged.
-   Bundle records `closedByPullRequestsReferences = [#3969]`.

**Recommended action**:

-   pass1: `keep-open` — feature is genuinely actionable on v4.10.0; auto-close once #3969 merges via `closed:fixed-by-pr-#3969`.
-   pass2 labels: `severity:medium,area:packaging,area:cli,state:in-progress`

---

<!-- subagent 1 -->

### #3440: Enhance `default_package_path` to serve multi-package projects better

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Re-read `default_package_path` against the request. The user wants name-based lookup with warnings when the package alias does not match the project name and a hard fail when no default and no `force-app` exist.

**Evidence**:

-   `cumulusci/core/config/project_config.py:517-525` — implementation is the simple "first packageDirectory with `default: true`" pattern; falls back to `force-app`, then `src`. No name-based lookup, no multi-package warning, no hard fail when both are missing.

**Recommended action**:

-   pass1: `keep-open` — same multi-package umbrella as #2979 / #3429; would best be solved together.
-   pass2 labels: `severity:low,area:packaging,area:sfdx,area:multi-package`

---

<!-- subagent 1 -->

### #3441: `cci task run create_package_version` should allow `version_base: default`

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Inspected `version_base` handling in `cumulusci/tasks/create_package_version.py` and the `release_unlocked_beta` flow definition in `cumulusci.yml`.

**Evidence**:

-   `cumulusci/tasks/create_package_version.py:63-112` — `version_base: Optional[str]`; documented values are `None`, a literal version number, or `latest_github_release`.
-   `cumulusci/tasks/create_package_version.py:529-563` — `_get_base_version_number` only branches on `None` (default) and `"latest_github_release"`; any other string is parsed as a literal version. There is no `"default"`/`"highest"` sentinel and no support for unsetting via flow override.
-   `cumulusci/cumulusci.yml:1216-1225` — `release_unlocked_beta` hard-codes `version_base: latest_github_release` for `create_package_version`. Per yippie's comment, CCI lacks a generic null-override mechanism for flow steps.

**Recommended action**:

-   pass1: `keep-open` — could be solved minimally with a `default`/`highest` sentinel in `_get_base_version_number`, or generalized as a CCI null-override feature.
-   pass2 labels: `severity:low,area:packaging,area:flow-overrides,area:cli`

---

<!-- subagent 3 -->

### #3446: CCI task push_qa crashes for Unlocked package with no namespace

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: `repro-pkg-b1-dev` (dev) — used to confirm push_qa even runs against a non-packaging org; the user's actual NoneType crash happens before the SOQL would succeed on a real packaging org.

**Method**:
The user's command omitted `--version` and `--version_id`. Inspected `cumulusci/tasks/push/tasks.py` `_run_task`: when neither is set, it calls `self._get_version(package, self.options.get("version"))`, which calls `self._parse_version(version)` on `version=None`, which calls `version.split(".")`. This raises `AttributeError: 'NoneType' object has no attribute 'split'` — exactly the error from the linked gist in the issue. Verified by direct unit-style invocation:

```python
BaseSalesforcePushTask._parse_version(None, None)  # -> AttributeError
```

Also ran `cci task run push_qa --orgs /tmp/repro_pkg_orgs.txt --metadata_package_id 0337S000000DUMMY --org repro-pkg-b1-dev` against the scratch org; the path failed earlier on the org (no Push API on a dev scratch — `sObject type 'MetadataPackage' is not supported`), but on a real Push-API-enabled DevHub it would surface the NoneType crash.

The user's follow-up comment ("Push API not activated by default") is a separate UX issue: when Push API is disabled, the SOQL `SELECT ... FROM MetadataPackage` fails with `INVALID_TYPE`. They'd like a friendlier error.

**Evidence**:

-   `cumulusci/tasks/push/tasks.py:33` — `version_parts = version.split(".")` (no None-guard above).
-   `cumulusci/tasks/push/tasks.py:283-297` — `_run_task` does not validate `version` before calling `_get_version`.
-   Test: `/tmp/repro/3/tests/repro_3446_push_qa_no_version.py` passes on v4.10.0.
-   Live invocation against scratch org: `Error: Malformed request ... sObject type 'MetadataPackage' is not supported` (orthogonal to the NoneType but illustrates the second comment).

**Recommended action**:

-   pass1: `keep-open` — real bug, simple fix.
-   pass2 labels: `bug`, `good-first-issue`

---

<!-- subagent 1 -->

### #3466: Ability to specify a test suite to run instead of just `test_name_match`

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Searched for `test_suite_names` in `cumulusci/tasks/apex/testrunner.py`. Wrote `/tmp/repro/1/tests/test_issue_3466.py` to assert the option exists, has a sensible description, and is mutually exclusive with `test_name_match`.

**Evidence**:

-   `cumulusci/tasks/apex/testrunner.py:173-175` — `test_suite_names` is a documented `task_options` field accepting a comma-separated list of ApexTestSuite names.
-   `cumulusci/tasks/apex/testrunner.py:188-190, 246-253, 308-376` — option is wired through `_init_options`, validated as mutually exclusive with `test_name_match`, and used by `_get_test_classes_from_test_suite_names` (queries ApexTestSuite + TestSuiteMembership).
-   Repro test passes (2/2) on v4.10.0.

**Recommended action**:

-   pass1: `closed:feature-implemented` — the request is fully covered. davidmreed's reply linked W-12214520; that backlog item appears to have shipped.
-   pass2 labels: `area:packaging,area:apex,state:resolved`

---

<!-- subagent 7 -->

### #3470: Rename `ci_master` to `ci_main` (or alias)

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

```823:835:cumulusci/cumulusci.yml
    ci_master:
        group: Continuous Integration
        description: Deploy the package metadata to the packaging org and prepare for managed package version upload.  Intended for use against main branch commits.
        steps:
            ...
```

`rg "ci_main"` returns no matches. davidmreed's 2022 reply indicated this requires flow-aliasing infrastructure first.

**Recommended action**:

-   pass1: `closed:stale-24mo` — 4yr stale; preserve as `closed:stale-24mo` rather than dismiss; the inclusive-language motivation is real and could be revisited if flow aliasing lands.
-   pass2 labels: `enhancement,stale,inclusive-language`

<!-- subagent 12 -->

### #3471: `Merged 0 commits into branch:` message displays when a non-Source Code change is

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: Bucket A — code-scan and `git log` against `cumulusci/tasks/github/merge.py`.

**Evidence**:

The reported log message originates from `_merge`:

```241:262:cumulusci/tasks/github/merge.py
    def _merge(self, branch_name, source, commit):
        """Attempt to merge a commit from source to branch with branch_name"""
        compare = self.repo.compare_commits(branch_name, commit)
        if not compare or not compare.files:
            self.logger.info(f"Skipping branch {branch_name}: no file diffs found")
            return

        try:
            self.repo.merge(branch_name, commit)
            self.logger.info(
                f"Merged {compare.behind_by} commits into branch: {branch_name}"
            )
        except GitHubError as e:
            if e.code != http.client.CONFLICT:
                raise

            if self.options["create_pull_request_on_conflict"]:
                self._create_conflict_pull_request(branch_name, source)
            else:
                self.logger.info(
                    f"Merge conflict on branch {branch_name}: skipping pull request creation"
                )
```

The log line at 251 reports `compare.behind_by` from github3's CompareCommits. `behind_by` is computed from the GitHub compare-commits endpoint and reflects how many commits the destination branch is behind the merged commit _as of the comparison's chosen merge-base_; for "effectively no-op" content merges (e.g. README/test.txt scenarios where downstream content already matches via merge-base), the API can return 0 even though `self.repo.merge(branch_name, commit)` at line 249 just shipped a real commit. The reporter's pattern (README and `test.txt` reproduce; cumulusci.yml / source-code changes do not) is consistent with this hypothesis.

`git log --all --oneline -- cumulusci/tasks/github/merge.py` since 2023-01-01 shows only refactors (ruff migration, internal repo migration, the `create_pull_request_on_conflict` option, `skip_future_releases` fixes); the `compare.behind_by` reporting line has not changed since the original `MergeBranch` implementation. Existing `test_merge.py` only exercises the happy path where `behind_by == 1`; no test covers the misleading 0-case.

**Recommended action**:

-   pass1: `keep-open` — small, well-localized fix (replace `compare.behind_by` with `len(list(compare.commits))` or report the SHA returned from `self.repo.merge(...)`); add a test covering the `behind_by=0` case.
-   pass2 labels: `bug, github, merge, low-priority`

---

<!-- subagent 12 -->

### #3479: Error with "cci org import" in github action

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: Bucket A — code-scan of `cumulusci/cli/org.py` `org_import`, `cumulusci/core/config/sfdx_org_config.py` `sfdx_info`, and `git log` for the relevant wrapping fix.

**Evidence**:

The reported error is the bare `Expecting value: line 1 column 1 (char 0)` (raw `json.JSONDecodeError`). The actual error path in v4.10.0:

`cumulusci/cli/org.py`:

```238:255:cumulusci/cli/org.py
@org.command(name="import", help="Import an org from Salesforce DX")
@click.argument("username_or_alias")
@orgname_option_or_argument(required=True)
@pass_runtime(require_keychain=True)
def org_import(runtime: CliRuntime, username_or_alias: str, org_name: str):
    # Import the org from the SFDX keychain as an SfdxOrgConfig
    # The `sfdx` key ensures we can reload using the right class.
    org_config = SfdxOrgConfig(
        {"username": username_or_alias, "sfdx": True},
        org_name,
        runtime.keychain,
        global_org=False,
    )

    # Determine if we received a locally-created scratch org
    # or some other org (which we'll treat as persistent)

    info = org_config.sfdx_info
```

`cumulusci/core/config/sfdx_org_config.py`:

```38:55:cumulusci/core/config/sfdx_org_config.py
        if p.returncode:
            self.logger.error(f"Return code: {p.returncode}")
            for line in stderr_list:
                self.logger.error(line)
            for line in stdout_list:
                self.logger.error(line)
            message = f"\nstderr:\n{nl.join(stderr_list)}"
            message += f"\nstdout:\n{nl.join(stdout_list)}"
            raise SfdxOrgException(message)

        else:
            try:
                org_info = json.loads("".join(stdout_list))
            except Exception as e:
                raise SfdxOrgException(
                    "Failed to parse json from output.\n  "
                    f"Exception: {e.__class__.__name__}\n  Output: {''.join(stdout_list)}"
                )
```

Both nonzero return codes and JSON parse failures from `sfdx org display --json` are wrapped in `SfdxOrgException` with explicit context (this wrapping landed in commit `017bc49f4` on 2020-11-24, well before the 2023-01-06 issue). The bare `Expecting value: line 1 column 1 (char 0)` symptom is therefore not what a v4.10.0 user would see for this scenario — they would get the `Failed to parse json from output. Exception: JSONDecodeError. Output: ...` message instead, which directly reveals the empty/garbled sfdx output and points to the upstream auth/shell problem.

David Reed's only reply (2023-02-22, never answered by the reporter) correctly identifies the root cause as GHA shell interpolation: `echo ${{ secrets.DEV_AUTH_URL }} > sfdx_auth` without quotes mangles multiline secrets, so `sfdx force:auth:sfdxurl:store` either fails silently or produces an invalid auth — then `sfdx org display --json` returns empty/non-JSON. Fix is in the user's workflow, not in cci.

**Recommended action**:

-   pass1: `closed:not-reproducible-on-v4.10.0` — root cause is user GHA workflow (unquoted multiline secret); cci's only relevant code path (`sfdx_info`) already wraps the error with a user-actionable message in v4.10.0; reporter never responded for 3+ years.
-   pass2 labels: `awaiting-more-details, external-config`

---

<!-- subagent 8 -->

### #3485: "cci task run run_tests" generates incorrect test_results.xml format

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: code-scan

**Evidence**:

-   `cumulusci/tasks/apex/testrunner.py:803-834` — `_write_output` opens `junit_output` and writes `'<testsuite tests="{}">\n'` with no `<?xml version=...?>` declaration and no enclosing `<testsuites>` element.
-   The closing tag at line 834 is `</testsuite>`. This exactly matches the malformed XML the reporter showed.
-   `junit_output` defaults to `test_results.xml` (line 201-203), unchanged.

**Recommended action**:

-   pass1: `keep-open` — small mechanical fix, still affects users producing JUnit reports for CI.
-   pass2 labels: `bug, area:apex, good-first-issue`

<!-- subagent 8 -->

### #3492: Enhance the "-o" option of "cci flow run" to accept "project\_\_custom" attribute values

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/cli/flow.py:152-162` — parses `-o` pairs by splitting key on `"__"` and unpacking into exactly two parts (`task_name, option_name = key.split("__")`).
-   A user passing `-o project__custom__myattr value` would actually error with "too many values to unpack" because the split yields three elements; even worded as `-o project__custom value` there is no codepath that writes into `project_config.config["project"]["custom"]`.
-   `coordinator = runtime.get_flow(flow_name, options=options)` (line 166) receives a `{task_name: {option_name: value}}` dict; project-level overrides have no entry point here.

**Recommended action**:

-   pass1: `keep-open` — legitimate usability gap for matrix-style CI.
-   pass2 labels: `enhancement, area:cli`

<!-- subagent 8 -->

### #3506: when clause support for flow steps which call other flows

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature (silent ignore = bug-shaped)
**Method**: code-scan

**Evidence**:

-   `cumulusci/core/flowrunner.py:660-672` — when the step has a `task:` key, the StepSpec is built with `when=step_config.get("when")`.
-   `cumulusci/core/flowrunner.py:674-697` — the `flow:` branch recurses via `_visit_step(...)` passing only `parent_options`, `parent_ui_options`, and `from_flow`; it never reads or propagates `step_config.get("when")`. Any `when:` clause attached to a flow-call step is silently dropped.

**Recommended action**:

-   pass1: `keep-open` — confirmed silent-failure foot-gun the user reported.
-   pass2 labels: `enhancement, area:flows`

<!-- subagent 2 -->

### #3518: Task add_picklist_entries always sets a default value for record types

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/tasks/metadata_etl/picklists.py`. The smoking gun is at
line 177: `default = str(process_bool_arg(entry.get("default", False))).lower`
— `.lower` is referenced as an attribute, not invoked. The resulting bound
method is truthy, so the `if default:` guard at line 214 always runs the
default-clobbering loop, marking the new entry as default for every record
type. Wrote two tests: a unit-level repro of the truthy bound-method, and a
function-level repro driving `_add_single_record_type_entries` directly via
`MetadataElement` to observe the mutated XML.

**Evidence**:

-   `cumulusci/tasks/metadata_etl/picklists.py:177` missing `()` after `.lower`.
-   `cumulusci/tasks/metadata_etl/picklists.py:214-221` unconditionally sets
    defaults whenever `default` is truthy.
-   Test output: `test_issue_3518_picklist_record_type_default_logic_bug`
    asserts the value is callable (it is) — fails as expected.
-   Test output: `test_issue_3518_record_type_default_not_set_when_default_false`
    observed `<default>true</default>` on a value that was passed
    `default: False`.

**Recommended action**:

-   pass1: keep-open — small targeted fix.
-   pass2 labels: `severity:high,area:metadata-etl,type:bug`

---

<!-- subagent 3 -->

### #3542: 2GP flows fail locally with "Could not find package version id"

**Verdict**: INCONCLUSIVE-needs-2GP-CI-pipeline
**Repro type**: bug
**Org used**: none (cannot easily fabricate a github status posted under a different SHA)

**Method**:
Read `cumulusci/tasks/github/commit_status.py` `GetPackageDataFromCommitStatus._run_task` and `cumulusci/core/github.py:get_version_id_from_commit`. The lookup uses `self.project_config.repo_commit` (the local checkout's git HEAD SHA) verbatim, then iterates `commit.status().statuses` for one matching the configured context. No fallback to parent commits or to `pull_request.head.sha`. If the upstream workflow posted the status under a different SHA — most commonly the synthetic merge SHA used by `actions/checkout` on `pull_request` triggers — the local lookup returns no version_id and the user sees the exact error from the issue.

git log shows several "github_package_data" commits since 2022 (last directly related: `33bb24197 Update default API version to v59.0`; `7686731b2 Use commit_status resolution strategy when building non-SkipValidation 2GPs`) but none change the SHA-resolution semantics. The cci-side code path is **unchanged** at v4.10.0.

Cannot fully reproduce in this run because that requires (a) a private repo configured to use a 2GP feature build workflow that records the version_id, (b) a PR build that has actually completed, (c) local checkout of that PR. Out-of-scope for a fresh scratch org repro.

**Evidence**:

-   `cumulusci/tasks/github/commit_status.py:20` — `commit_sha = self.project_config.repo_commit`
-   `cumulusci/core/github.py:361-368` — `get_version_id_from_commit` only checks the exact SHA's statuses; no fallback.

**Recommended action**:

-   pass1: `unchanged` — needs the reporter (or someone with a 2GP CI pipeline) to confirm whether their workflow posts under merge-commit SHA vs head-commit SHA. If the latter, this is a cci bug; if the former, it's a workflow alignment bug in `cumulus-actions`.
-   pass2 labels: `needs-repro`, `2gp`

---

<!-- subagent 2 -->

### #3543: New Option `load_sfdx_project_paths` for dx_convert_from Task

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Read `cumulusci/tasks/dx_convert_from.py` end to end (27 lines). Greped for
`load_sfdx_project_paths|resolve_sfdx_package_dirs|sfdx_project` across the
codebase.

**Evidence**:

-   `cumulusci/tasks/dx_convert_from.py:7-14` exposes only `extra` and
    `src_dir`; no `load_sfdx_project_paths` / `resolve_sfdx_package_dirs`.
-   The grep hits in `project_config.py` and `cli/project.py` are unrelated
    (general sfdx-project.json reading); they aren't wired into
    `DxConvertFrom`.

**Recommended action**:

-   pass1: keep-open — feature still unimplemented; reporter offered a draft PR.
-   pass2 labels: `severity:low,area:metadata-etl,type:enhancement`

---

<!-- subagent 6 -->

### #3544: `update_admin_profile` errors when org has Person Accounts AND a namespace

**Verdict:** `INCONCLUSIVE-needs-namespaced-project`

### Original symptom

When `cci flow run dev_org --org dev` is run against a scratch org that has both:

1. `PersonAccounts` in `features` array of the scratch_def
2. `namespaced: true` set under `orgs/scratch/<name>` in `cumulusci.yml`

…then the `update_admin_profile` step of `config_dev` fails. The reporter cited stackoverflow Q 206310 noting "Entity of type 'RecordType' named 'Account.Business_Account' cannot be found", indicating the deployed Profile XML references a record type that has been renamed or removed by SFDX/MetadataAPI behavior in PersonAccounts orgs.

Internal tracking: davidmreed filed W-12589033 (2023-02-22) but stated "I can't make any promises about delivering a behavior change."

### Provisioning attempted

```text
$ uv run cci org info repro-special-c-pa
config_file: orgs/person_accounts.json
config_name: person_accounts
namespaced:  False
features:    Communities, PersonAccounts, ContactsToMultipleAccounts
instance_url: https://drive-inspiration-9525.scratch.my.salesforce.com
```

CumulusCI's own `cumulusci.yml` declares no `project__package__namespace`. Setting `namespaced: true` on the scratch config has no effect without a registered namespace, and registering a CumulusCI namespace in CCIDevHub is out of scope for this triage pass.

### Partial repro on v4.10.0

```text
$ uv run cci task run update_admin_profile --org repro-special-c-pa
Beginning task: ProfileGrantAllAccess
Extracting existing metadata...
[Done]
Loading transformed metadata...
Beginning task: Deploy
[InProgress]: Processing Type: Profile
[Done]
[Success]: Succeeded
```

The task **succeeded** against a non-namespaced PersonAccounts scratch org — confirming that the bug requires the _intersection_ of PersonAccounts + namespacing, not PersonAccounts alone.

### Code search for fixes

-   `git log --since=2023-02-01 -- cumulusci/tasks/salesforce/update_profile.py cumulusci/files/admin_profile.xml` shows only one commit (entrypoints refactor 23295c0a2) — no functional change to PersonAccounts handling.
-   `git log --grep "person.account|business_account|3544|W-12589033" -i` returns nothing relevant in `update_profile.py`.
-   `update_profile.py` retains a generic `person_account_default` option (line 242, 277) for explicit recordType configuration but no automatic detection or filtering of `Account.Business_Account` for PersonAccounts orgs.

### Adjacent finding (not the same bug)

`cumulusci/utils/__init__.py:229`:

```229:229:cumulusci/utils/__init__.py
    namespaced_org = namespace + "__" if namespaced_org else ""
```

Passing `-o namespaced_org True` against a project with `namespace=None` raises `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'`. Distinct from #3544's bug (which is a deploy-time RecordType-not-found error, not an init-time TypeError). Worth filing as a separate cleanup issue.

### Recommendation

-   **Pass 1:** needs-info — ask reporter to validate against v4.10.0 with their namespaced project and confirm whether the issue persists. Include `wi-created` already on the issue (W-12589033).
-   **Pass 2 label:** `needs-namespaced-project` — repro requires a namespaced project that this triage pipeline cannot synthesize.
-   Alternative: consider treating as `wontfix` per davidmreed's recommendation (use `flows.config_dev.steps.2: task: None` workaround) until SFDC fixes the underlying SFDX/MetadataAPI Account.Business_Account renaming issue.

<!-- subagent 8 -->

### #3549: Deploy to Salesforce does not create a test output

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/tasks/salesforce/Deploy.py:49-94` — exposes `test_level` and `specified_tests` options and validates them.
-   `cumulusci/tasks/salesforce/Deploy.py:150-154` — passes them through to the metadata API call but never captures `runTestResult`/`runTestsResult` from the response.
-   `rg "junit_output|test_results"` against `cumulusci/tasks/salesforce/Deploy.py` and `cumulusci/salesforce_api/metadata.py` returns no test-output writer for the deploy path.

**Recommended action**:

-   pass1: `keep-open` — natural feature; tracks #3564.
-   pass2 labels: `enhancement, area:metadata-deploy`

<!-- subagent 5 -->

### #3561: Retrieve_unpackaged unusable in MetaDeploy

**Verdict**: NOT-REPRODUCED-on-v4.10.0 (fix landed)
**Repro type**: bug
**Org used**: none

**Method**:
Read `cumulusci/tasks/salesforce/RetrieveUnpackaged.py`. Current code:

```26:36:cumulusci/tasks/salesforce/RetrieveUnpackaged.py
    def _init_options(self, kwargs):
        super(RetrieveUnpackaged, self)._init_options(kwargs)

        if "package_xml" in self.options:
            with open(self.options["package_xml"], "r") as f:
                self.options["package_xml_content"] = f.read()

    def _get_api(self):
        return self.api_class(
            self, self.options["package_xml_content"], self.options.get("api_version")
        )
```

`git log -S "package_xml_content" -- cumulusci/tasks/salesforce/RetrieveUnpackaged.py` -> commit `56e10665e` "Fix retrieve unpackaged so it is usable in metadeploy (#3566)" merged 2024-05-20 by yippie (the original issue reporter). The fix introduces `package_xml_content` as a separate option so the path-typed `package_xml` is preserved across multiple `_init_options` invocations.

**Recommended action**:

-   pass1: `close-as-fixed` with link to PR #3566.
-   pass2 labels: (none)

**Notes**: yippie shipped their own fix; the issue was just never closed.

---

<!-- subagent 8 -->

### #3570: Feature Request: Flow "finally" or "error" path

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/core/flowrunner.py` — only `ignore_failure` (mapped to `StepSpec.allow_failure`, line 122/144) and the `finally:` Python clause inside `flow.run()` (line 500) handle failures. There is no flow-step type for `finally:` / `on_error:` / `cleanup:` / `always_run`. `rg "finally|on_error|on_failure|always_run"` confirms.
-   `_run_step` (line 503-536) re-raises on `result.exception` if not `allow_failure`, which is the only failure handling.

**Recommended action**:

-   pass1: `keep-open` — design-level feature, but problem is real (rollback, notify on partial failure).
-   pass2 labels: `enhancement, area:flows`

<!-- subagent 2 -->

### #3585: Error Occurs when Using `update_package_xml` on object with `xsi:nil="true"`

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Wrote a test that places a `.object` file containing
`<customTabListAdditionalFields xsi:nil="true"/>` (with no `xmlns:xsi`
declared) and invokes `PackageXmlGenerator`. The underlying parser raises a
parse error because the `xsi:` prefix is unbound.

**Evidence**:

-   `cumulusci/tasks/metadata/package.py:115-130` — when a folder has objects
    it instantiates the registered parser; for `objects/` the parser uses the
    metadata tree which is strict about namespaces.
-   Test output: `test_issue_3585_xsi_nil_true_breaks_update_package_xml` fails
    with the exact "not well-formed (invalid token)" class of error reported
    by the user.

**Recommended action**:

-   pass1: keep-open — needs either a namespace-shim before parsing or
    pre-stripping of `xsi:nil` attributes.
-   pass2 labels: `severity:medium,area:metadata-etl,type:bug,sfdx-compat`

---

<!-- subagent 3 -->

### #3587: Warning when install_class/uninstall_class set with managed=false on update_package_xml

**Verdict**: NOT-REPRODUCED-on-v4.10.0 (feature still unimplemented)
**Repro type**: feature
**Org used**: none (update_package_xml is a local task)

**Method**:
Inspected `cumulusci/tasks/metadata/package.py`:

-   `PackageXmlGenerator.render_xml()` lines 142-152: emits `<postInstallClass>/<uninstallClass>` only when `self.managed and self.install_class` / `self.managed and self.uninstall_class`. No warning if managed is False.
-   `UpdatePackageXml._init_options` line 587-588: only normalizes `managed` to bool. No validation/warning.
-   `UpdatePackageXml._init_task` line 590-610: passes options through without checking the install_class+managed=False combination.

Confirmed live by running:

```bash
uv run cci task run update_package_xml --install_class MyInstall --uninstall_class MyUninstall
```

Output (full): `Beginning task: UpdatePackageXml; Generating src/package.xml from metadata in src` — **no warning**. (src/package.xml ended up empty because src/ has no metadata in the cci repo, but the relevant signal is the absence of any warning about install_class being silently dropped.)

Also confirmed via direct generator test (`/tmp/repro/3/tests/repro_3587_update_package_xml_no_warning.py`):

-   `managed=False, install_class="X"` → output XML has neither `<postInstallClass>` nor `<uninstallClass>`.
-   `managed=True, install_class="X"` → output XML has them.

**Evidence**:

-   `cumulusci/tasks/metadata/package.py:142-152`
-   `cumulusci/tasks/metadata/package.py:578-610`
-   Live cci output: no warning when invoked with --install_class but no --managed.

**Recommended action**:

-   pass1: `keep-open` — feature still missing.
-   pass2 labels: `enhancement`, `good-first-issue`

---

<!-- subagent 1 -->

### #3593: `dx` task doesn't work for some commands like `project convert source`

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/tasks/sfdx.py` end-to-end. Wrote `/tmp/repro/1/tests/test_issue_3593.py` that constructs an `SFDXOrgTask` with command `"project convert source -r src -d force-app"` and a `ScratchOrgConfig`, then asserts the resulting command would not append a target-org flag.

**Evidence**:

-   `cumulusci/tasks/sfdx.py:46-51` — `SFDXOrgTask._get_command` unconditionally appends `" -o {username}"` for any `ScratchOrgConfig`, regardless of whether the underlying sf subcommand accepts a target-org flag.
-   Repro test FAILS with the resulting command: `sf project convert source -r src -d force-app -o test@example.com` — the same shape that the issue reporter said sf cli rejects.
-   Note: `cumulusci/tasks/dx_convert_from.py` (which backs the OOTB `dx_convert_from` task) was switched to extend `SFDXBaseTask` (no org), so the OOTB task is fine; the bug remains for any user-defined task that uses `SFDXOrgTask` with a no-org sf subcommand.

**Recommended action**:

-   pass1: `keep-open` — needs an opt-out option (e.g. `pass_org: False` or a `no_org_command` whitelist). Verifying actual sf cli rejection of `-o` for `project convert source` would need an org/sf cli; the CCI side of the bug is unchanged.
-   pass2 labels: `severity:medium,area:packaging,area:sfdx,area:dx-task,state:needs-design`

---

<!-- subagent 3 -->

### #3600: Allow install_managed to use environment variables

**Verdict**: NOT-REPRODUCED-on-v4.10.0 (feature still unimplemented)
**Repro type**: feature
**Org used**: `repro-pkg-b1-dev` (dev) — used to confirm cci accepts the literal `${VAR}` value at runtime.

**Method**:
Inspected the option-processing path:

-   `cumulusci/core/tasks.py:35` — `PROJECT_CONFIG_RE = re.compile(r"\$project_config.(\w+)")`. This is the only substitution pattern.
-   `cumulusci/core/tasks.py:127-157` — `_init_options.process_options` only calls `PROJECT_CONFIG_RE.sub(...)`; no env-var lookup.
-   `cumulusci/utils/yaml/safer_loader.py:60` — uses plain `yaml.safe_load(...)` with no custom resolver.
-   `cumulusci/tasks/salesforce/install_package_version.py:31-34` — `version` option description does not mention env-var support.

Confirmed live by:

```bash
export MY_FAKE_VERSION='1.2.3'
uv run cci task run install_managed --version '${MY_FAKE_VERSION}' \
    --namespace npsp --org repro-pkg-b1-dev --interactive True
```

Interactive prompt printed: `Package to install: npsp ${MY_FAKE_VERSION}` — literal, **not** expanded.

**Evidence**:

-   `cumulusci/core/tasks.py:35` — only substitution pattern.
-   `cumulusci/utils/yaml/safer_loader.py:60` — plain yaml load.
-   Test: `/tmp/repro/3/tests/repro_3600_install_managed_no_env_var.py` passes.
-   Live interactive output: `Package to install: npsp ${MY_FAKE_VERSION}`.

**Recommended action**:

-   pass1: `keep-open` — feature still missing. Note design decision required: `$env:VAR` (consistent with `$project_config.X`) vs `${VAR}` (POSIX) vs `os.path.expandvars` semantics; backwards-compat for any literal `$`-strings.
-   pass2 labels: `enhancement`

---

<!-- subagent 11 -->

### #3603: Any issue with git results in the unhelpful "404 not found" error

**Bucket**: A. **Type**: bug. **Verdict**: REPRODUCED-on-v4.10.0 (partial).

The user enumerated five situations (1) source repo missing, (2) dep repo
missing, (3) source ref/tag/branch missing, (4) dep resolution strategy fails,
(5) source resolution strategy fails — all collapsing into a generic 404 with
no source/URL/ref context. Code-scan + targeted unit test confirm:

-   Cases **1, 2** are already wrapped: both `cumulusci/core/dependencies/github.py::get_repo`
    and `cumulusci/core/source/github.py::GitHubSource.__init__` catch `NotFoundError`
    and raise `DependencyResolutionError("We are unable to find the repository at {url}...")`.
    Fixed long ago by commit `738d4a8a4` (2021).
-   Case **5** for the `release:` source spec is wrapped at
    `source/github.py:103` ("Could not find release {self.spec.release}.").
-   Case **3** is **NOT** wrapped. `source/github.py:126`
    `self.commit = self.repo.ref(ref).object.sha` lets a raw `NotFoundError`
    bubble out. The repro test (`test_case3_source_ref_not_found_message_quality`)
    prints the actual exception:

    ```
    Exception type: NotFoundError
    Message: '404 [No message]'
    ```

    Neither the repo URL nor the missing ref/tag is present.

-   Case **4** raises `DependencyResolutionError(f"Unable to resolve dependency {dependency}")`
    (resolvers.py:663). The dependency description is included, but the list of
    attempted strategies is not — so the user can't immediately tell which
    strategy fell through.

Recommendation: keep-open. Two clean, scoped fixes available (wrap `repo.ref()`
in `source/github.py`; enrich the resolvers.py:663 message with strategy
names). Good-first-issue territory.

Repro: `/tmp/repro/11/tests/test_3603_404_messages.py` (4 tests; all pass).

---

<!-- subagent 11 -->

### #3604: Task request: Update sfdx-project.json dependencies based off of computed cumulusci dependencies

**Bucket**: A. **Type**: feature. **Verdict**: REPRODUCED-on-v4.10.0 (gap still
present).

`uv run cci task list` returns 0 tasks that write `sfdx-project.json`. A
project-wide grep for `unpackagedMetadata` returns no matches. Maintainer
acknowledged the request as W-13504384 in a 2023 reply, label `wi-created`
already on the issue, but no implementation has shipped through v4.10.0.

Recommendation: keep-open (`enhancement`, `wi-created` already attached).

Repro: code-scan only; no test file (feature gap, nothing to assert against).

---

<!-- subagent 1 -->

### #3605: Ability to Increment Major Versions when running `upload_production`

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Inspected `cumulusci/tasks/salesforce/package_upload.py`. Wrote `/tmp/repro/1/tests/test_issue_3605.py` to assert `major_version` and `minor_version` task options exist and the major-bump branch is wired in `_validate_versions`.

**Evidence**:

-   `cumulusci/tasks/salesforce/package_upload.py:39-46` — `major_version` and `minor_version` are documented `task_options`.
-   `cumulusci/tasks/salesforce/package_upload.py:101-140` — `_validate_versions` honors a major-version bump, defaulting `minor_version` to `"0"` when the user supplies a higher major.
-   Repro test passes (3/3).
-   Closing PR identified by `git log` history: commit `87b94440e` — "Deploy Major and Minor Version option in upload_production task (#3651)".

**Recommended action**:

-   pass1: `closed:fixed-by-pr-#3651` — feature shipped; user can run `cci task run upload_production -o major_version 34 -o minor_version 0`.
-   pass2 labels: `area:packaging,area:1gp,state:resolved`

---

<!-- subagent 8 -->

### #3607: The `retry_failures` from the task `run_tests` is not working for me

**Verdict**: INCONCLUSIVE-needs-org-with-managed-package
**Repro type**: bug
**Method**: code-scan + unit test

**Evidence**:

-   `cumulusci/tasks/apex/testrunner.py:209-222` — `retry_failures` strings are compiled into regexes at task init.
-   `cumulusci/tasks/apex/testrunner.py:400-408` — `_is_retriable_failure` checks both `Message` and `StackTrace` via `re.search`.
-   `cumulusci/tasks/apex/testrunner.py:475-490` — increments `counts["Retriable"]` for each matching failure.
-   `cumulusci/tasks/apex/testrunner.py:548` — printed as `Retried: {Retriable}`.
-   Repro test `/tmp/repro/8/tests/test_3607_retry.py` confirms in pure Python that `re.compile("UNABLE_TO_LOCK_ROW").search(user_message)` returns a match for the exact message body the user pasted. Both tests pass.
-   One escape hatch in code: `cumulusci/tasks/apex/testrunner.py:448-452` — for class-level errors with `managed: true` (which the user has), retries are explicitly skipped. The user's failure shows per-test details, so this should not have been the cause.

**Recommended action**:

-   pass1: `closed:stale-24mo` — code logic is correct as written; reporter has not engaged in 30+ months; cannot reproduce without their managed package + org.
-   pass2 labels: `bug, area:apex, needs-info`

<!-- subagent 8 -->

### #3609: Command 'cci task run dx --command "plugins:install ..."' fails

**Verdict**: INCONCLUSIVE-needs-live-cli-test
**Repro type**: bug
**Method**: code-scan

**Evidence**:

-   `cumulusci/tasks/sfdx.py:20` — `SFDX_CLI = "sf"` (changed from `sfdx` in the v4.x cutover; reporter was on 3.76.0).
-   `cumulusci/tasks/sfdx.py:34-40` — `_get_command` is a thin wrapper: `f"sf {self.options['command']}"`. The CCI layer adds nothing that could introduce the "Timed out after 30000 ms" error the user saw.
-   `cumulusci/cumulusci.yml:273-275` — `dx` task is registered as `cumulusci.tasks.sfdx.SFDXOrgTask` with description "Execute an arbitrary Salesforce DX command".
-   Reporter's literal command `--command "plugins:install ..."` uses the colon syntax that `sfdx` accepted; `sf` typically wants `plugins install`. Different CLI now.

**Recommended action**:

-   pass1: `closed:stale-24mo` — not a CCI bug; CCI faithfully shells out. CLI in question has changed substantially since.
-   pass2 labels: `bug, upstream:sf-cli`

<!-- subagent 8 -->

### #3612: Maintain the CumulusCI for VSCode Extension

**Verdict**: NOT-REPRODUCED-on-v4.10.0
**Repro type**: feature (wrong repo)
**Method**: code-scan

**Evidence**:

-   Issue body explicitly references `https://github.com/SFDO-Tooling/cci-vscode`. That is a separate repository; nothing in this CumulusCI tree is responsible for it.

**Recommended action**:

-   pass1: `closed:not-reproducible-on-v4.10.0` — should be re-filed against `SFDO-Tooling/cci-vscode`.
-   pass2 labels: `enhancement, wontfix, wrong-repo`

<!-- subagent 5 -->

### #3613: AddFieldsToPageLayout — "Cannot find metadata file"

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug (UX/error-message)
**Org used**: `repro-etl-b-dev`

**Method**:
Live repro: `uv run cci task run add_page_layout_fields --org repro-etl-b-dev -o api_names "Account"` against the scratch org. Saved at `/tmp/repro/5/tests/issue-3613/output-just-object.txt`. Result: `Error: Cannot find metadata file /var/.../retrieve/layouts/Account.layout`. Same task with `-o api_names "Account-Account Layout"` succeeds end-to-end (deploy succeeds). The functionality is intact; the user-visible bug is the unhelpful error when the api_name does not match the Metadata API's `<Object>-<LayoutName>` file naming convention.

The error originates from `MetadataSingleEntityTransformTask._transform` (base.py:332): `if not path.exists(): raise CumulusCIException(f"Cannot find metadata file {path}")`. The retrieve actually succeeded (the user's report says "metadata is getting downloaded"), but `_transform` looks for the user's typed api_names verbatim as filenames.

**Recommended action**:

-   pass1: `improve-error-message` — keep open as a UX bug.
-   pass2 labels: `bug`, `good-first-issue`

**Notes**: Two complementary improvements would help:

1. In `_transform` (base.py:332), include the actual list of files retrieved into `source_metadata_dir` in the error message so the user can spot the naming mismatch.
2. In `AddFieldsToPageLayout._init_options`, warn when an api_name does not contain `-` (Layout API names always do).

The user was on Windows in 2023 — note that the user might also have been hitting a backslash path issue, but the underlying class of bug is the same: api_name format mismatch.

---

<!-- subagent 11 -->

### #3615: update_dependencies does not honor resolution strategy

**Bucket**: A. **Type**: bug (filed). **Verdict**: NOT-REPRODUCED-on-v4.10.0.

The user expected `cci task run update_dependencies --resolution_strategy preproduction`
to install a beta of an Unlocked dependency. In `cumulusci/cumulusci.yml`:

```yaml
dependency_resolutions:
    preproduction: latest_release
    production: latest_release
    resolution_strategies:
        latest_release: [tag, latest_release, unmanaged] # no latest_beta
        include_beta: [tag, latest_beta, latest_release, unmanaged]
```

So `preproduction` is an alias for the `latest_release` stack and intentionally
omits `latest_beta`. To install the beta unlocked package, the correct
invocation is `--resolution_strategy include_beta`. The repro test confirms
all three properties: `preproduction` lacks `latest_beta`, `include_beta` has
it, and `preproduction == production`. Working as documented.

Recommendation: closed:not-reproducible-on-v4.10.0. Possible follow-up: docs/UX
improvement (the name `preproduction` is misleading; consider clarifying in
docs/data.md or renaming to `release_only` in a future major).

Repro: `/tmp/repro/11/tests/test_3615_preproduction_strategy.py` (3 tests; all
pass).

---

<!-- subagent 8 -->

### #3618: Allow for list when deleting/removing CumulusCI orgs

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/cli/org.py:519-545` — `org_remove` decorated with `@orgname_option_or_argument(required=True)`, takes a single `org_name`.
-   `cumulusci/cli/org.py:605-625` — `org_scratch_delete` same pattern, single `org_name`.
-   No `nargs=-1`, no comma-split helper; passing `org1,org2` would be treated as a single literal alias and fail keychain lookup.

**Recommended action**:

-   pass1: `keep-open` — legitimately useful for cleanup workflows; small implementation surface.
-   pass2 labels: `enhancement, area:cli, good-first-issue`

<!-- subagent 11 -->

### #3619: Dependency_pins does not honor passwords

**Bucket**: A. **Type**: bug. **Verdict**: REPRODUCED-on-v4.10.0.

Two distinct reproducible defects in `cumulusci/core/dependencies/dependencies.py`:

1. **Parsing error (Part A)**: `GitHubDependencyPin` (L81-101) declares only
   `github: str` and `tag: str`. Adding `password_env_name:` to a
   `dependency_pins:` entry triggers
   `DependencyParseError: Unable to parse dependency pin: {...}` from
   `parse_dependency_pin()`.

2. **Silent password drop (Part B)**: When a dynamic dependency carries a
   `password_env_name`, the pin path at L171-187 short-circuits to
   `pin.pin(self, context)`, which (L100) calls
   `GitHubTagResolver().resolve(d, context)` directly — bypassing
   `resolve_dependency()`'s password-propagation block (resolvers.py L644-654).
   The resulting `package_dependency.password_env_name` is `None`, so
   `PackageNamespaceVersionDependency.install()`'s
   `os.environ.get(self.password_env_name)` runs against `None` and the
   install-key is never sent.

The contrast test confirms the non-pinned path _does_ propagate the password,
isolating the defect to `pin.pin()`.

Recommendation: keep-open. Two-line fix sketch:

-   Add `password_env_name: Optional[str] = None` to `GitHubDependencyPin`.
-   In `pin.pin()`, after `d.ref, d.package_dependency = ...`, mirror the
    block from resolvers.py L644-654 to copy
    `d.password_env_name` (or the pin's own) onto `d.package_dependency`.

Repro: `/tmp/repro/11/tests/test_3619_pin_password.py` (4 tests; all pass).

---

<!-- subagent 10 -->

### #3649: Support serial loads with update_data task

**Verdict:** `REPRODUCED-on-v4.10.0` — feature still unimplemented

`UpdateData.load_data` and the rollback path in `cumulusci/tasks/bulkdata/update_data.py:184` and `:211` both call `get_dml_operation(..., api_options={}, ...)` with the `api_options` dict hardcoded empty. `BulkApiDmlOperation` in `step.py` honors `api_options["bulk_mode"]` for Serial/Parallel selection, but `UpdateData` never sets it. `LoadData` and the snowfakery channel runner DO let users pick `bulk_mode`; `update_data` is the gap.

The author offered to implement. Fix is small (~10 lines): add `bulk_mode` (or `api_options`) to `UpdateData.task_options` and pipe it into both `get_dml_operation` calls.

**Recommended pass1: `keep-open`** with `good-first-issue` label.

<!-- subagent 8 -->

### #3663: When clause | Ability to pass in prior task response values

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/core/flowrunner.py:510-516` — the `when` Jinja context is hardcoded to `{"project_config": ..., "org_config": ...}`. Prior step results (`self.results`) are not exposed.
-   The `^^task.return_value` resolver lives elsewhere (option resolution path) and is not threaded into the `when` evaluator.

**Recommended action**:

-   pass1: `keep-open` — natural extension of `when`; complements #3506.
-   pass2 labels: `enhancement, area:flows`

<!-- subagent 2 -->

### #3692: No parser configuration found for subdirectory digitalExperiences

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Greped `digitalExperiences|digitalExperience` across the codebase — zero
hits. Wrote two tests: a static one asserting `digitalExperiences` is a key
in `metadata_map.yml`, and a runtime one that creates the folder structure
and runs `PackageXmlGenerator`.

**Evidence**:

-   `cumulusci/tasks/metadata/metadata_map.yml` has no `digitalExperiences`
    key.
-   `cumulusci/tasks/metadata/package.py:115-118` raises
    `MetadataParserMissingError("No parser configuration found for
subdirectory %s")`.
-   Test output: `test_issue_3692_digital_experiences_in_metadata_map` fails
    on the missing key; runtime test reproduces the exact error message from
    the user report.

**Recommended action**:

-   pass1: keep-open — add `digitalExperiences` (and likely
    `digitalExperienceConfigs`) entries to `metadata_map.yml` with
    appropriate parser classes (probably a bundle parser).
-   pass2 labels: `severity:medium,area:metadata-etl,type:bug`

---

<!-- subagent 10 -->

### #3699: Sort of the data during extraction

**Verdict:** `REPRODUCED-on-v4.10.0` — feature missing, but workaround exists

`ExtractData._soql_for_mapping` (extract.py:133-147) builds the SOQL with `WHERE` only — no `ORDER BY`. `MappingStep` has no `order_by`/`sort` field. However, `append_filter_clause` strips a leading `WHERE` from `soql_filter` and concatenates the remainder onto the query, which means a user can write `soql_filter: "Active__c = true ORDER BY CreatedDate"` and it produces valid SOQL. So the missing capability is "first-class `order_by` field for parity with `where`", not "ability to sort at all".

The author hasn't followed up since 2023-11; with a working workaround, this is low-priority.

**Recommended pass1: `closed:stale-24mo`.** Reopen later if a v5 effort wants explicit `order_by` for declaration ergonomics.

<!-- subagent 10 -->

### #3700: Trying to do an upsert on a master-detail child object gets an error around permission

**Verdict:** `REPRODUCED-on-v4.10.0` — bug

`MappingStep._get_required_permission_types(operation)` in `mapping_parser.py:373-377` returns `("updateable", "createable")` for any operation in `(UPSERT, ETL_UPSERT)` (or any mapping action of the same). Master-detail lookup fields in Salesforce are `createable: True` but `updateable: False` (you cannot reparent a master-detail child after creation). `_check_field_permission` therefore returns `False` for the MD lookup field on an upsert mapping, and `_validate_field_dict` errors out with the exact message the user reported: "Field xxx\_\_c does not have the correct permissions ('updateable', 'createable') for this operation."

Repro test (`/tmp/repro/10/tests/test_3700_master_detail_upsert_perm.py`) constructs an `UPSERT` mapping for an `Order__c` with an `Account__c` master-detail lookup, simulates a `{createable: True, updateable: False}` describe, and asserts that `_check_field_permission` returns `False` — assertion passes.

**Recommended pass1: `keep-open`** with `good-first-issue`. Fix: when validating an MD lookup field for an upsert, accept `createable` alone (the lookup never gets updated post-insert anyway). A field-shape detector can use `relationshipName` + `cascadeDelete: True` from describe.

<!-- subagent 10 -->

### #3701: set a mapping to the id instead of it being either a number or the salesforce id

**Verdict:** `REPRODUCED-on-v4.10.0` — feature gap

`MappingStep` and the extract/load pipeline special-case the literal field name `"Id"` in many places (`mapping_parser.py:171/190/228/241/422`); it always represents the Salesforce Id and lands in an `sf_id` column. There is no mechanism to make a different field (an external-id like `BCM_Unique_Id__c`) act as the row's primary key in the extracted SQLite. The user's example yaml `Id : BCM_Unique_Id__c` is currently interpreted as "extract the SF Id into the column named `BCM_Unique_Id__c`", not "make `BCM_Unique_Id__c` the row primary key".

This is closely tied to #3699 (motivated by sortable git diffs of dataset extracts). The deeper PK-replacement feature would touch many places in extract / load / lookup-resolution.

**Recommended pass1: `closed:stale-24mo`.** Reporter hasn't followed up since 2023-11. Workarounds are available (extract Id into a known column and post-process). Could revisit if a v5 effort tackles dataset diff-ability holistically.

<!-- subagent 12 -->

### #3717: Github automerge feature task not working when running through Github Flow

**Verdict**: INCONCLUSIVE-needs-cumulus-actions-workflow
**Repro type**: bug
**Method**: Bucket A — code-scan of `cumulusci/core/config/project_config.py` `repo_info` / `repo_branch` and repo-wide grep for GitHub Actions env-var auto-detection.

**Evidence**:

The reporter notes that `project_config.repo_branch` and `project_config.project__git__prefix_feature` are `None` when `ci_feature` / `github_automerge_feature` is triggered by a merge event in a GitHub Actions workflow, but populated when triggered manually via the Actions tab.

`cumulusci/core/config/project_config.py` shows that cci's only CI auto-detection is for Heroku:

```220:255:cumulusci/core/config/project_config.py
    def repo_info(self) -> Dict[str, Any]:
        if self._repo_info is not None:
            return self._repo_info

        # Detect if we are running in a CI environment and get repo info
        # from env vars for the environment instead of .git files
        info = {"ci": None}

        # Make sure that the CUMULUSCI_AUTO_DETECT environment variable is
        # set before trying to auto-detect anything from the environment
        if not os.environ.get("CUMULUSCI_AUTO_DETECT"):
            self._repo_info = info
            return self._repo_info

        # Heroku CI
        heroku_ci = os.environ.get("HEROKU_TEST_RUN_ID")
        if heroku_ci:
            info = {
                "branch": os.environ.get("HEROKU_TEST_RUN_BRANCH"),
                "commit": os.environ.get("HEROKU_TEST_RUN_COMMIT_VERSION"),
                "ci": "heroku",
                "root": "/app",
            }

        # Other CI environment implementations can be implemented here...

        self._apply_repo_env_var_overrides(info)
```

A repo-wide grep (`Grep` over `cumulusci/`) for `GITHUB_REF|GITHUB_HEAD_REF|GITHUB_SHA|GITHUB_ACTIONS` returns **zero matches** — there is no GitHub Actions environment auto-detection in cci. The fallback path in `repo_branch` (line 394-402) calls `current_branch(self.repo_root)` which reads `.git/HEAD`. On a `push`-triggered GHA workflow the standard `actions/checkout@v4` checkout puts the working copy in a detached HEAD state, so `current_branch` returns `None`. On `workflow_dispatch` triggered manually, the action receives a `ref` input that resolves to a named branch checkout, so `current_branch` works.

Net: the reporter's symptom is exactly what cci produces unless the workflow sets `CUMULUSCI_REPO_BRANCH` (and friends) explicitly before invoking `cci flow run`. That responsibility lives in the `cumulus-actions/standard-workflows` YAMLs, not in cci. This matches the precedent established in #3418 (also `INCONCLUSIVE-needs-cumulus-actions-workflow`).

**Recommended action**:

-   pass1: `unchanged` — issue is at the cci ↔ cumulus-actions boundary; needs investigation in `cumulus-actions/standard-workflows` to confirm/fix `CUMULUSCI_REPO_BRANCH` plumbing for `push`-triggered child-feature merges.
-   pass2 labels: `external-config, cumulus-actions, needs-info`

> Optional follow-up enhancement (not part of triage): add a `# GitHub Actions` block in `repo_info` parallel to the Heroku block, reading `GITHUB_HEAD_REF` (PR) / `GITHUB_REF_NAME` (push) and `GITHUB_SHA`. Would close a class of "branch=None in CI" reports including this one, but is a behavior-change to a long-stable contract and merits its own design discussion.

<!-- subagent 1 -->

### #3721: `create_package_version` `version_name` default should be version number, not "Release"

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Searched for `version_name` defaults in `create_package_version.py` and `package_upload.py`, and for any jinja2 templating in PackageUpload. Verified the muselab-d2x commit that implements the requested behavior is not an ancestor of HEAD.

**Evidence**:

-   `cumulusci/tasks/create_package_version.py:184` — `version_name=self.options.get("version_name") or "Release"`. Default is still the literal string `"Release"`.
-   `cumulusci/cumulusci.yml:684-686` — `upload_production` hard-codes `name: Release`.
-   `cumulusci/tasks/salesforce/package_upload.py:147-154` — passes `VersionName` straight through; no jinja2/template support.
-   `git merge-base --is-ancestor 7aaf348f3 HEAD` returns non-zero. Commit `7aaf348f3` ("Change version naming on PackageUpload task to use the predicted version number and a jinja2 template expression") lives only on the `d2x/*` remotes (muselab-d2x fork), per jlantz's 2024 comment.

**Recommended action**:

-   pass1: `keep-open` — needs upstream port + design (templating? plain version number? both 1GP and 2GP?).
-   pass2 labels: `severity:low,area:packaging,area:1gp,area:2gp`

---

<!-- subagent 3 -->

### #3734: upload_production fails with FIELD_INTEGRITY_EXCEPTION when latest is Beta patch

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none (would require a 1GP packaging org with both 6.13 Released and 6.13.1 Beta — too large to fabricate)

**Method**:
Read `cumulusci/tasks/salesforce/package_upload.py` `PackageUpload._validate_versions`. The "latest version" SOQL query orders `MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, ReleaseState DESC LIMIT 1`. When the user has the pattern they describe (release 6.13, then create patch 6.13.1 Beta as a safety net), the query returns the patch row with `ReleaseState='Beta'`.

Then at line 134-135:

```python
if version["ReleaseState"] == "Beta":
    self.options["minor_version"] = str(version["MinorVersion"])
```

This sets `minor_version=13`, identical to the already-Released minor. The PackageUploadRequest is then created with major=6, minor=13, which Salesforce rejects with `FIELD_INTEGRITY_EXCEPTION: The version number must be greater than the last Managed - Released version number: 6.13`. Exactly the error in the issue.

The user's own analysis in their last 3 comments is correct and matches the code. The current `cannot-reproduce`/`awaiting-more-details` labels are stale.

Confirmed via mocked unit test `/tmp/repro/3/tests/repro_3734_upload_production_beta_patch.py`:

-   With `{Major=6, Minor=13, Patch=1, ReleaseState=Beta}` → `_validate_versions` sets `minor_version='13'` (the bug).
-   With `{Major=6, Minor=13, Patch=None, ReleaseState=Released}` → `_validate_versions` sets `minor_version='14'` (the desired behavior).

git log shows `87b94440e Deploy Major and Minor Version option in upload_production task (#3651)` (2023-09-19) added the major/minor options but did not change the latest-version query or the Beta-branch logic. v4.10.0 still has this code as-is.

**Evidence**:

-   `cumulusci/tasks/salesforce/package_upload.py:80-98` — SOQL query, `ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, ReleaseState DESC LIMIT 1`.
-   `cumulusci/tasks/salesforce/package_upload.py:134-137` — Beta branch sets `minor_version` to the same minor.
-   Test passes on v4.10.0 with mocked `_get_one_record`.

**Recommended action**:

-   pass1: `keep-open` — confirmed real bug; remove the stale `cannot-reproduce`/`awaiting-more-details` labels.
-   pass2 labels: `bug`

---

## Summary cross-cutting findings

1. **Two feature requests (#3587, #3600)** are easy "good-first-issue" candidates whose semantics are clear from the issue body. Both are independently verifiable with no org needed (`update_package_xml` is local; env-var support is a parser-level concern).
2. **Two real bugs (#3446, #3734)** still reproduce on v4.10.0 with stable, well-understood root causes. #3734 is mislabeled `cannot-reproduce` — that label should be removed in pass2.
3. **Two cross-stack issues (#3418, #3542)** point at the boundary between cci and the `cumulus-actions/standard-workflows` repo. They cannot be triaged from cci alone; they need either a workflow-side check or a request to the reporter for the workflow file/SHAs they're using.

<!-- subagent 4 -->

### #3745: ci_beta and install_managed_beta do not use the latest beta

**Verdict:** `NOT-REPRODUCED-on-v4.10.0` (working as designed)

**Evidence:** [`/tmp/repro/4/evidence/3745-source-and-design.txt`](/tmp/repro/4/evidence/3745-source-and-design.txt)

The `install_managed_beta` task (cumulusci.yml line 408) sets `version: latest_beta`, which `InstallPackageVersion` (lines 96–100 of `cumulusci/tasks/salesforce/install_package_version.py`) resolves via a GitHub Releases lookup using the `include_beta` resolver strategy — NOT a direct DevHub query for the latest `Package2Version`:

```96:101:cumulusci/tasks/salesforce/install_package_version.py
        if version in ["latest", "latest_beta"]:
            strategy = "include_beta" if version == "latest_beta" else "production"
            dependency = GitHubDynamicDependency(github=github)
            dependency.resolve(
                self.project_config, get_resolver_stack(self.project_config, strategy)
            )
```

The reporter (kayla-hager, 2024-02-07) ran `create_package_version` standalone — bypassing `release_2gp_beta` — so no GitHub release with the beta tag was ever created, hence `ci_beta` correctly fell back to the latest production tag (1.27). Comments resolve this as a documentation/usability issue; the reporter accepted the explanation 2024-02-13 and indicated they would close. v4.10.0 has not changed this behavior.

**Recommendation:** keep `closed:stale-24mo` (rule 1). No code defect.

---

<!-- subagent 4 -->

### #3746: Deleted Versions used for determining next version

**Verdict:** `REPRODUCED-on-v4.10.0` (code-level confirmation)

**Evidence:** [`/tmp/repro/4/evidence/3746-source-soql.txt`](/tmp/repro/4/evidence/3746-source-soql.txt)

The reporter (yippie, 2024-02-09) flagged that `create_package_version._get_base_version_number()` does not filter `IsDeprecated = true` when picking the highest existing `Package2Version` to increment from. The bug is present verbatim in v4.10.0 source at `cumulusci/tasks/create_package_version.py` lines 535–541:

```529:545:cumulusci/tasks/create_package_version.py
    def _get_base_version_number(
        self, version_base: Optional[str], package_id: str
    ) -> PackageVersionNumber:
        """Determine the "base version" of the package (existing version to be incremented)"""
        if version_base is None:
            # Default: Get the highest existing version of the package
            res = self.tooling.query(
                "SELECT MajorVersion, MinorVersion, PatchVersion, BuildNumber, IsReleased "
                "FROM Package2Version "
                f"WHERE Package2Id='{package_id}' "
                "ORDER BY MajorVersion DESC, MinorVersion DESC, PatchVersion DESC, BuildNumber DESC "
                "LIMIT 1"
            )
            if res["size"]:
                return PackageVersionNumber(
                    **res["records"][0], package_type=PackageType.SECOND_GEN
                )
```

The same file at line 297 DOES include `IsDeprecated = FALSE` for `Package2` lookups, so the project knows about the column — the omission at line 535 is asymmetric and matches the report exactly. End-to-end repro on a real packaging org would require creating two Package2Version records and deleting one (sf package version delete), which is outside this triage's scope. Code-level confirmation is sufficient.

**Recommendation:** flip currently-proposed `closed:stale-24mo` → `kept-open` with `severity:medium`, `area:packaging`, `target:v4-patch`. Trivial 1-line fix (add `AND IsDeprecated = false` to the SOQL WHERE clause).

---

<!-- subagent 8 -->

### #3754: Enable configuration for cci version update sources

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/cli/utils.py:65-79` — `get_latest_final_version` hits `https://pypi.org/pypi/cumulusci/json` literally, no env-var, no kwarg.
-   `cumulusci/cli/utils.py:82-101` — `check_latest_version` cannot be disabled via flag/env. Workaround in the comments (touch `~/.cumulusci/cumulus_timestamp` to a far-future epoch) confirmed by inspecting the timestamp logic at lines 38-50, 86-89.

**Recommended action**:

-   pass1: `keep-open` — easy add (e.g. `CUMULUSCI_DISABLE_VERSION_CHECK` env), helps offline/restricted environments.
-   pass2 labels: `enhancement, area:cli`

<!-- subagent 1 -->

### #3758: Flow `push_upgrade_org` is incorrectly defined

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read the `push_upgrade_org` flow in `cumulusci/cumulusci.yml`. Wrote `/tmp/repro/1/tests/test_issue_3758.py` to load the YAML and assert the final step calls `config_managed` (not `config_qa`).

**Evidence**:

-   `cumulusci/cumulusci.yml:1161-1177` — final step is `flow: config_qa`. The bug report (correctly, in my view) argues this should be `config_managed` because push upgrades target managed-package orgs (UAT sandboxes), not QA scratch orgs.
-   Repro test FAILS with `config_qa` != `config_managed`.
-   Both flows currently expand to the same steps (`deploy_post`, `update_admin_profile`, `load_sample_data`), so behavior is equivalent today, but semantics drift over time and the docs link customers to the wrong flow page.

**Recommended action**:

-   pass1: `keep-open` — single-line YAML fix; great `good-first-issue` candidate. Out of scope for this triage pass per task constraints (do not fix bugs).
-   pass2 labels: `severity:medium,area:packaging,area:flows,good-first-issue`

---

<!-- subagent 5 -->

### #3762: `update_admin_profile` task fails on namespaced org with Person Accounts enabled

**Verdict**: closed:duplicate-of-#3544
**Repro type**: bug
**Org used**: none (dup-confirm only per protocol)

**Method**:
Read both #3762 and (via gh) #3544. The reporter (noahisapilot) explicitly self-identifies the duplicate in their first comment dated 2024-03-06: _"Apologies, this seems like a duplicate of #3544"_. Both report the same root cause: `update_admin_profile` errors when deploying to a namespaced scratch org with `PersonAccounts` enabled, because the retrieved profile contains record types like `Account.Business_Account` (no namespace) but the task injects the namespace prefix onto recordType references during deploy.

The reporter's own analysis even pinpoints the offending code at `update_profile.py` line 238 (in v3.84.3; corresponds to `rt["record_type"] = rt["record_type"].format(**self.namespace_prefixes)` at line 236 in v4.10.0).

#3544 is still OPEN at v4.10.0 with `wi-created` label `W-12589033`.

**Recommended action**:

-   pass1: `close-as-duplicate` — link to #3544.
-   pass2 labels: (n/a — duplicate)

**Notes**: Per dup-confirm protocol, no live repro performed.

---

<!-- subagent 10 -->

### #3768: Snowfakery Batch Size and Just Once

**Verdict:** `REPRODUCED-on-v4.10.0` — bug, structural

The Snowfakery channel runner architecturally creates a separate working directory per batch via `shutil.copytree(template_path, data_dir)` (`queue_manager.py:322`). Before that copy, `Snowfakery._cleanup_object_tables` (`snowfakery.py:721-730`) drops every non-`sf_ids` table from the template. So when batch 2+ starts, the SQLite database carried in the template only contains `sf_ids` mapping tables — none of the actual `account`-row data created in the initial just_once batch.

Snowfakery's `random_reference: Account` resolves at generation time against rows in the recipe-local database. Since `just_once: true` means batch 2+ does not regenerate the Accounts, and the carried-over database has no `account` rows (just the `account_sf_ids` map), `random_reference` has nothing to pick from in batch 2+. This matches the user's exact symptom: first 20 contacts (one batch) get the 5 just_once Accounts, the next 430 get nothing (or fall back to NPSP defaults).

Verifying interactively against an org would require provisioning a scratch and running the recipe at `--batch_size 20 --num_records 450` — code-review evidence is conclusive without it. **Recommended pass1: `keep-open`**, severity major. Fix likely requires preserving rows of just_once-referenced objects (not just `_sf_ids`) in the template DB carried to subsequent batches; coordination with the Snowfakery dev branch is probably required.

<!-- subagent 2 -->

### #3771: find_replace transforms on XPath with predicates does not work

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/core/source_transforms/transforms.py:415-485`. The
`transform_xpath` helper splits the XPath on `/`, wraps each tag in
`*[local-name()=...]`, and re-appends the predicate verbatim. The bug: tag
references INSIDE the predicate (e.g. `price` in `[price>40]`) are still
namespace-bound, so on default-`xmlns` documents they don't match. PR #3772
(referenced in `closedByPullRequestsReferences`) lives only on the `leboff`
fork and was never merged into `main`.

**Evidence**:

-   `cumulusci/core/source_transforms/transforms.py:420-435` — naive
    predicate handling.
-   `git log --all --oneline --grep="3772\|3771\|XPath.*predicate"` shows
    only `2bf6ce6a3 Improve namespace handling in find_replace` on
    `remotes/leboff/feature/improve-find-replace-ns-handling`; not on
    origin/main.
-   Test output: `test_issue_3771_xpath_predicate_with_xmlns_resolves`
    observed 0 matches (or 5 wrong matches) for the user-supplied xpath on
    namespaced XML.

**Recommended action**:

-   pass1: keep-open — the leboff PR is a viable starting point; or implement
    the reporter's "strip xmlns then re-add" approach for simplicity.
-   pass2 labels: `severity:medium,area:source-transforms,type:bug,has-pr`

---

<!-- subagent 2 -->

### #3773: retrieve_profile task seems to be missing some Metadata

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/salesforce_api/retrieve_profile_api.py` end to end. The
`_queries_retrieve_permissions` method (lines 164-195) builds queries for
`SetupEntityAccess`, `ObjectPermissions`, `PermissionSetTabSetting`, and a
flow-specific `SetupEntityAccess`. There is no `FieldPermissions` query.
Wrote a test that asserts `fieldpermissions` appears in the joined query
text.

**Evidence**:

-   `cumulusci/salesforce_api/retrieve_profile_api.py:164-195` — no
    `FieldPermissions` query.
-   Greped `FieldPermission|field_permission|fieldPermission` — only the
    `update_profile.py`, `permissions.py`, and `mapping_parser.py` files
    reference field permissions; `retrieve_profile_api.py` does not.
-   Test output: `test_issue_3773_retrieve_profile_queries_field_permissions`
    shows the four queries built by the function and confirms none include
    `FieldPermissions`.

**Caveat**: This is a code-level repro. Final end-to-end confirmation
(profile XML actually missing AccountContactRelation field perms) would
require a real org with a profile that has only field-level (not
object-level) permissions on AccountContactRelation. Code evidence is
conclusive, however, because objects with no `ObjectPermissions` row never
make it into the package.xml requested for retrieve.

**Recommended action**:

-   pass1: keep-open — needs additional `FieldPermissions` query plus
    inclusion of those parent SObjectTypes in the `CustomObject` retrieve set.
-   pass2 labels: `severity:medium,area:retrieve-profile,type:bug`

---

<!-- subagent 8 -->

### #3852: CumulusCI 4 refresh token error (sarge Capture.flush)

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: code-scan + runtime probe

**Evidence**:

-   `pyproject.toml:52` — `"sarge"` pinned with no version constraint.
-   `uv run python -c "import sarge; print(sarge.__version__)"` → `0.1.7.post1`.
-   `uv run python -c "import sarge; print(hasattr(sarge.Capture, 'flush'))"` → `False`. The upstream fix (`def flush(self): pass`) sits unreleased on master.
-   `cumulusci/core/config/sfdx_org_config.py:200-214` — `refresh_oauth_token` still calls `self.sfdx_info` at line 212. Per the maintainer comment in-thread, on Python 3.13 this triggers the `AttributeError: 'Capture' object has no attribute 'flush'` during interpreter shutdown logging path — cosmetic only, no functional regression.

**Recommended action**:

-   pass1: `keep-open` — kept-open per maintainer label; track until sarge 0.1.8 ships or we vendor/swap the dependency.
-   pass2 labels: `bug, upstream:sarge, py313`

<!-- subagent 8 -->

### #3854: Issue while Capturing Data (capture_sample_data lookup_key validation)

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Method**: code-scan

**Evidence**:

-   `cumulusci/tasks/bulkdata/extract.py:367-374` — the offending validation block is intact:
    -   `if total_mapping_operations != total_rows: raise ConfigError(f"Total mapping operations ({total_mapping_operations}) do not match total non-empty rows ({total_rows}) for lookup_key: {lookup_key}. Mention all related tables for lookup: {lookup_key}")`
-   Error text matches the user's report verbatim.
-   Per swirkens' comment, this validation was introduced in PR #3741 / commit `2c5d0056e` and remains unchanged in v4.10.0.
-   Workaround in thread: pin to CCI 3.84.1 (pre-validation).

**Recommended action**:

-   pass1: `keep-open` — kept-open per maintainer label; real bug for polymorphic-lookup users.
-   pass2 labels: `bug, area:bulkdata, regression`

<!-- subagent 4 -->

### #3884: Running a Dev_Org flow goes through re-install of the same package version again

**Verdict:** `INCONCLUSIVE-needs-project-with-managed-deps`

**Evidence:** [`/tmp/repro/4/evidence/3884-source-skip-logic.txt`](/tmp/repro/4/evidence/3884-source-skip-logic.txt)

The reporter (dipakparmar, 2025-02-26) describes that re-running `dev_org` reinstalls dependencies that are already installed. CumulusCI itself has no `project__dependencies` block, so end-to-end repro on this very repo is not possible. Source review against v4.10.0 shows that BOTH managed-package install paths in `cumulusci/core/dependencies/dependencies.py` already have a "skip if already at this or newer version" guard:

```458:465:cumulusci/core/dependencies/dependencies.py
        if org.has_minimum_package_version(
            self.namespace,
            version,
        ):
            context.logger.info(
                f"{self} or a newer version is already installed; skipping."
            )
            return
```

```513:520:cumulusci/core/dependencies/dependencies.py
        if any(
            self.version_id == v.id
            for v in itertools.chain(*org.installed_packages.values())
        ):
            context.logger.info(
                f"{self} or a newer version is already installed; skipping."
            )
            return
```

Likely the reporter conflated "Resolving dependencies..." log noise (which always prints) and the unconditional `deploy_unmanaged` / `config_dev` steps in the dev_org flow with managed-package reinstalls. Without a customer project that has managed deps to reproduce against, we cannot disprove a corner case (e.g., `installed_packages` cache invalidation across a particular path).

**Recommendation:** keep the proposed `closed:missing-fields` (rule 3) verdict. The original report lacks the customer's `cumulusci.yml` excerpt that would let us see which dependency type they were observing reinstall.

---

<!-- subagent 11 -->

### #3886: Required Dependencies?

**Bucket**: A. **Type**: bug (UX/log-noise). **Verdict**:
REPRODUCED-on-v4.10.0.

The `[select]` extras (`numpy`, `pandas`, `annoy`, `scikit-learn`) are not in
the default install. `cumulusci/tasks/bulkdata/select_utils.py` L14-30 emits
`logger.warning("Optional dependencies are missing...")` at module-import time
in the `try/except ImportError`. Two transitive imports
(`mapping_parser` and `step`) pull in `select_utils`, and `extract.py` imports
both, so **every** `extract_dataset` invocation triggers the warning even when
no select strategy is configured.

Behavior introduced in PR #3858 / commit `89a5b5ddb` (W-17427085) and
unchanged through v4.10.0. The reporter's quoted text mentioned
`pipx upgrade cumulusci[select]`; v4.10.0 now uses `get_cci_upgrade_command()`
which adapts to the install method (e.g. `pip install --upgrade cumulusci[select]`),
so that part of the message has been polished — but the noise persists.

Recommendation: keep-open. Mitigations to consider:

-   Move the warning emission out of module-import and into the code path that
    actually consumes optional deps (e.g. inside the relevant similarity
    strategy or `Annoy`-using step), so it only fires when the user opts into
    `select` strategies.
-   Or downgrade to `logger.debug` and add a one-line
    `logger.warning` only at the point of need.

Repro: `/tmp/repro/11/tests/test_3886_select_warning.py` (2 tests; all pass).

This issue was double-tagged in `themes.md` (bulkdata + dependencies);
classified under dependencies here per bundle instructions.

<!-- subagent 1 -->

### #3889: Uninstall 2GP task request

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: feature

**Method**:
Listed all `Uninstall*` task definitions in `cumulusci.yml` and inspected `UninstallPackage.py` and `UninstallPackageZipBuilder` to see whether any task accepts a 04t SubscriberPackageVersionId.

**Evidence**:

-   `cumulusci/cumulusci.yml:615-642` — Uninstall tasks: `uninstall_managed`, `uninstall_packaged`, `uninstall_packaged_incremental`, `uninstall_src`, `uninstall_pre`, `uninstall_post`. None take a 04t id.
-   `cumulusci/tasks/salesforce/UninstallPackage.py:6-32` — `UninstallPackage` accepts only `namespace` (and `purge_on_delete`). Builds an `UninstallPackageZipBuilder` from the namespace.
-   `cumulusci/salesforce_api/package_zip.py:290-301` — `UninstallPackageZipBuilder` writes destructiveChanges referencing `InstalledPackage` by namespace; no 04t code path.
-   Tooling API `SubscriberPackageVersion` delete or sf cli `package uninstall -p 04t...` is the underlying API the user wants; not wrapped by any CCI task.

**Recommended action**:

-   pass1: `keep-open` — needs a new `UninstallPackageVersion` task (or extend `UninstallPackage`) that calls Tooling API directly so it doesn't depend on sf cli stability (per the user's note about sf cli breaking changes).
-   pass2 labels: `severity:medium,area:packaging,area:2gp,area:unlocked-package`

<!-- subagent 4 -->

### #3899: Exception in task deploy_packaging.unschedule_apex

**Verdict:** `INCONCLUSIVE-needs-1gp-packaging-org`

**Evidence:** [`/tmp/repro/4/evidence/3899-task-and-error-analysis.txt`](/tmp/repro/4/evidence/3899-task-and-error-analysis.txt)

The `unschedule_apex` task (cumulusci/cumulusci.yml lines 646–651) runs one line of trivial Apex via the Tooling API:

```650:650:cumulusci/cumulusci.yml
            apex: "for (CronTrigger t : [SELECT Id FROM CronTrigger]) { System.abortJob(t.Id); }"
```

Ran cleanly against scratch org `repro-pkg-b2-dev` ("Anonymous Apex Executed Successfully!"). The reporter's error references Salesforce platform-internal Java classes (`system.scheduler.cron.JobType`, `common.udd.constants.CronJobTypeEnum`) — this is a Salesforce platform NullPointerException inside the scheduler subsystem when looking up a CronTrigger's job-type implementation. CCI sends correct Apex; the platform fails to execute it on certain 1GP packaging org configurations. Provisioning a 1GP packaging org via OAuth connected app is outside the scope of this triage.

**Recommendation:** keep `kept-open`. Add a Pass-2 `external/upstream-salesforce` label (or equivalent) so future triage knows the root cause is upstream. Could also be a candidate for "close as not-our-bug" once a Salesforce known-issue reference is found.

---

<!-- subagent 6 -->

### #3902: `install_managed` `security_type` not respected with 04t ID

**Verdict:** `INCONCLUSIVE-needs-managed-package-04t`

### Original symptom

User reports that running `install_managed` with `--version '04t…'` and `--security_type NONE` yields a tab visible to non-admin profiles, whereas the same install with `--version '1.11.2'` (namespace+version) honors `NONE`.

### Code-only evidence on v4.10.0

`InstallPackageVersion._init_options` (cumulusci/tasks/salesforce/install_package_version.py) builds `PackageInstallOptions` from task options including `security_type`:

```148:148:cumulusci/tasks/salesforce/install_package_version.py
        self.install_options = PackageInstallOptions.from_task_options(self.options)
```

`PackageInstallOptions.from_task_options` (cumulusci/salesforce_api/package_install.py:67–92) parses `security_type` into the `SecurityType` enum where `SecurityType.ADMIN = "NONE"`.

For 04t versions, `_run_task` routes to `PackageVersionIdDependency.install(...)` which calls `install_package_by_version_id(...)` -> `_install_package_by_version_id(...)`. The latter posts the option to the Tooling API:

```165:175:cumulusci/salesforce_api/package_install.py
    request = PackageInstallRequest.create(
        {
            "EnableRss": options.activate_remote_site_settings,
            "NameConflictResolution": options.name_conflict_resolution,
            "Password": options.password,
            "SecurityType": options.security_type,
            ...
        }
    )
```

Runtime serialization confirmed in the venv:

```text
$ uv run python -c "import json; from cumulusci.salesforce_api.package_install import SecurityType; print(json.dumps({'SecurityType': SecurityType.ADMIN}))"
{"SecurityType": "NONE"}
```

`SecurityType` is a `StrEnum` (cumulusci/core/enums.py) with `__str__ = str.__str__`, so JSON serializes via the string base — `SecurityType.ADMIN` -> `"NONE"`. This was hardened previously in commit `502290b8d` (Dec 2022) for Python 3.11 enum changes and again in `402b890e0` (StrEnum migration).

The 04t and namespace+version paths each correctly pass `security_type` to their respective Salesforce APIs (Tooling API `PackageInstallRequest.SecurityType` for 04t, package install zip header for namespace+version). No defect identified in CumulusCI v4.10.0.

### Why INCONCLUSIVE

We do not have a known reusable managed package 04t Id installable into a CCIDevHub-derived scratch to verify the user's runtime observation. Per spec, this verdict is allowed when the prerequisite cannot be provisioned within budget.

### Possible non-CumulusCI explanations (worth recording for the issue)

-   Salesforce Tooling API treatment of `SecurityType=NONE` may differ between fresh installs and upgrades: existing components retain their previously assigned profile permissions on upgrade. If the package was previously installed at a lower version with `SecurityType=FULL`, upgrading with `NONE` may not retroactively restrict access to existing tabs.
-   Tab visibility for managed-package tabs can be controlled by App-level visibility (Profile `applicationVisibilities` / `tabVisibilities`) independent of object-level CRUD/FLS, which is what `SecurityType` governs.
-   Package metadata may include `Profile` deltas that explicitly grant tab access regardless of the install-time SecurityType.

### Recommendation

-   **Pass 1:** needs-info — request reporter to (a) confirm whether the package was being upgraded vs freshly installed, and (b) inspect Salesforce setup audit trail to see the actual `PackageInstallRequest.SecurityType` value at install time.
-   **Pass 2 label:** `needs-managed-package-fixture` — without an internal reusable managed package 04t fixture, this class of issue can never be deterministically validated by maintainers.

---

<!-- subagent 4 -->

### #3929: create_community Loop/Timeout During Community Creation

**Verdict:** `NOT-REPRODUCED-on-v4.10.0`

**Evidence:** [`/tmp/repro/4/evidence/3929-create_community.log`](/tmp/repro/4/evidence/3929-create_community.log)

Ran the exact reproduction command against scratch org `repro-pkg-b2-dev`:

```bash
uv run cci task run create_community --org repro-pkg-b2-dev \
  -o name "TestWebsite" -o template "Customer Service" -o url_path_prefix "testwebsite"
```

Community `0DBRK000000QtNR4A0` was created in ~117 seconds with normal polling escalation (1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 seconds) and exited the poll loop cleanly. No 300-second timeout, no retry. This matches the OP-thread comment from dipakparmar (2025-10-22): "This issue is no longer happening" — referring to the upstream SF CLI / Communities API fix tracked at forcedotcom/cli#3419.

**Recommendation:** flip currently-proposed `kept-open` → `closed:not-reproducible-on-v4.10.0` (NEW Pass-1 vocabulary per spec amendment). Confirmed working end-to-end with the very command the reporter said hung.

<!-- subagent 5 -->

### #3931: Specifying a profile in cumulusci.tasks.salesforce.ProfileGrantAllAccess results in an error

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: none (Python unit repro is sufficient — code path is purely local XML transform)

**Method**:
Read `cumulusci/tasks/salesforce/update_profile.py`. Spotted the suspect line:

```290:292:cumulusci/tasks/salesforce/update_profile.py
                for elem in tree.findall("layoutAssignments"):
                    if elem.find("recordType").text == rt["record_type"]:
                        elem.layout.text = layout_option
```

`elem.find("recordType")` returns `None` whenever a `layoutAssignments` element has no `recordType` child (which is valid metadata — a layoutAssignments without recordType applies to records lacking a record-type binding). The subsequent `.text` then raises `AttributeError: 'NoneType' object has no attribute 'text'` — exactly the user's reported error.

Wrote `/tmp/repro/5/tests/issue-3931/repro_unit.py` that builds an in-memory profile XML matching that shape (one `<layoutAssignments>` with `<layout>Account-Account Layout</layout>` and no recordType, plus one with both children) and calls `_set_record_types`. Output:

```
Traceback (most recent call last):
  File "/tmp/repro/5/tests/issue-3931/repro_unit.py", line 64, in main
    task._set_record_types(tree, "Admin")
  File "...update_profile.py", line 291, in _set_record_types
    if elem.find("recordType").text == rt["record_type"]:
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AttributeError: 'NoneType' object has no attribute 'text'
REPRODUCED: AttributeError raised: 'NoneType' object has no attribute 'text'
```

**Recommended action**:

-   pass1: `keep-open` — small, contained fix.
-   pass2 labels: `bug`

**Notes**: Minimal fix at update_profile.py:290-293 — bind `rt_elem = elem.find("recordType")` and check `if rt_elem is not None and rt_elem.text == rt["record_type"]`. Worth a quick scan of sibling code in `_set_record_types` for similar None-deref patterns on optional XML children.

---

<!-- subagent 10 -->

### #3936: HTTPSConnectionPool Read timed out (kept-open)

**Verdict:** `INCONCLUSIVE-needs-flaky-network` — but a structural gap is confirmed

`get_simple_salesforce_connection` in `cumulusci/salesforce_api/utils.py:13-51` constructs `simple_salesforce.Salesforce(...)` with no timeout kwarg and only retries `502/503/504` via `Retry(total=5, backoff_factor=0.3)`. No CCI-side task option, project setting, or env var exposes connect / read timeout for Salesforce REST or Bulk API calls. `cumulusci.yml` has no `timeout` entry.

The reported error `Read timed out. (read timeout=None)` with `timeout=None` typically means the proxy / VPN closed the socket while the client was waiting, not that a client-side timeout was hit. CCI cannot mitigate this without (a) exposing a configurable timeout to short-circuit zombie connections, and (b) extending the `Retry` to also cover read-timeout errors and bulk-job-polling failures.

The structural gap (no exposed timeout) is REPRODUCED. The actual flaky behavior is environment-dependent (corporate VPN) and not reproducible in CI without that environment.

This issue is already maintainer-labelled `kept-open`. **Recommended pass1: `unchanged`**. v5 candidacy: yes — add timeout option to `get_simple_salesforce_connection` and to bulk-job polling, plus a documented `cci org refresh` retry path for VPN-induced disconnects.

<!-- subagent 2 -->

### #3938: Rest_Deploy ignores errors

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/salesforce_api/rest_deploy.py`. Wrote a test that constructs
a `RestDeploy` instance with mocked task/org_config and patches
`requests.get` to return a JSON payload with `deployResult.status == "Failed"`
and a `componentFailures` list.

**Evidence**:

-   `cumulusci/salesforce_api/rest_deploy.py:101-120` —
    `_monitor_deploy_status` logs `componentFailures` then `return`s without
    raising.
-   `cumulusci/salesforce_api/rest_deploy.py:75-85` — `__call__` only logs
    when initial POST is non-201; never raises.
-   Test output: `test_issue_3938_rest_deploy_failure_does_not_raise` exits
    the patched call with no exception, confirming the silent-success bug.

**Recommended action**:

-   pass1: keep-open — CRITICAL severity; should raise `MetadataApiError` /
    `MetadataComponentFailure` on Failed status, mirroring the SOAP
    `ApiDeploy` behavior.
-   pass2 labels: `severity:critical,area:rest-deploy,type:bug,silent-failure`

---

<!-- subagent 2 -->

### #3939: Deploy task can't parse SOAP Response

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug

**Method**:
Read `cumulusci/salesforce_api/metadata.py:67-78` (`BaseMetadataApiCall.__call__`)
and `cumulusci/salesforce_api/metadata.py:425-546`
(`ApiDeploy._process_response`). The parser correctly raises
`ApexTestException` on Apex test failures (line 540) and
`MetadataApiError`/`MetadataComponentFailure` for other failure shapes
(lines 509, 520, 544). But every one of those exceptions is caught by the
generic `except Exception as e:` at line 73 and re-raised as
`MetadataParseError("Could not process MDAPI response: ...")`. The wrapping
matches the exact message text in the user report.

**Evidence**:

-   `cumulusci/salesforce_api/metadata.py:71-76` — wraps every exception
    thrown inside `_process_response`.
-   `cumulusci/salesforce_api/metadata.py:509,520,540,544` — places where
    intentional MDAPI exceptions are raised inside `_process_response`.
-   Test output: `test_issue_3939_deploy_apex_test_failure_swallowed`
    observed final message
    `Could not process MDAPI response: Apex Test Failure: Class.MyTestClass.testIt: line 12, column 1`
    which is the exact bug pattern.

**Recommended action**:

-   pass1: keep-open — the wrapping `except Exception` should re-raise CCI's
    own `CumulusCIException` subclasses (`MetadataApiError`,
    `MetadataComponentFailure`, `ApexTestException`) untouched and only wrap
    truly unexpected errors.
-   pass2 labels: `severity:high,area:salesforce-api,type:bug,error-handling`

<!-- subagent 5 -->

### #3951: set_duplicate_rule_status broken

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug (UX/error-message)
**Org used**: `repro-etl-b-dev`

**Method**:
Live repro using the exact CLI from the bug report:

```
uv run cci task run set_duplicate_rule_status --org repro-etl-b-dev \
  -o api_names "Standard_Rule_for_Leads_with_Duplicate_Contacts" \
  -o active False
```

Result (saved at `/tmp/repro/5/tests/issue-3951/output-no-prefix.txt`):

```
Error: Cannot find metadata file /var/.../retrieve/duplicateRules/Standard_Rule_for_Leads_with_Duplicate_Contacts.duplicateRule
```

Identical error wording as the user's report. Then ran the same command with the canonical Metadata API format `Lead.Standard_Rule_for_Leads_with_Duplicate_Contacts` — the task succeeded end-to-end (extract → transform → deploy → Success). The `SetDuplicateRuleStatus` task itself is functional; the bug is the unhelpful error when the user omits the `<Object>.` prefix that DuplicateRule API names require.

Same root cause as #3613 (api_name format mismatch surfaces as the generic `Cannot find metadata file` from `MetadataSingleEntityTransformTask._transform` base.py:332).

**Recommended action**:

-   pass1: `improve-error-message` — keep open.
-   pass2 labels: `bug`, `good-first-issue`, `documentation`

**Notes**: Two improvements:

1. Update the `set_duplicate_rule_status` task option help to call out the `<Object>.<RuleName>` format requirement.
2. Same as #3613 — improve the base.py:332 error to list the files actually retrieved.

The `Cannot find metadata file` error is shared across most `MetadataSingleEntityTransformTask` subclasses, so a single base-class fix would benefit several issues at once.

---

<!-- subagent 5 -->

### #3953: add_picklist_entries never works through CLI

**Verdict**: REPRODUCED-on-v4.10.0
**Repro type**: bug
**Org used**: `repro-etl-b-dev`

**Method**:
Live repro using the exact CLI from the bug report:

```
uv run cci task run add_picklist_entries --org repro-etl-b-dev \
  -o picklists "Account.Status__c" \
  -o entries '[{"fullName": "TestValue", "label": "Test Value"}]'
```

Result (saved at `/tmp/repro/5/tests/issue-3953/output.txt`):

```
Error: The 'fullName' key is required on all picklist values.
```

Identical to user's report.

Root cause confirmed by reading `cumulusci/tasks/metadata_etl/picklists.py`:

-   Line 51: `process_list_arg(self.options["picklists"])` — runs through the list-arg parser.
-   Line 68: `if not all(["fullName" in entry for entry in self.options["entries"]])` — iterates `entries` directly without parsing.
-   The CLI passes `entries` through as a JSON string. Iteration walks characters of `'[{"fullName": "TestValue", ...}]'`; none of the characters contain the substring `"fullName"`; `all(...)` returns False; error raised.

**Recommended action**:

-   pass1: `keep-open` — single-line fix.
-   pass2 labels: `bug`, `good-first-issue`

**Notes**: Minimal fix in `AddPicklistEntries._init_options`: `if isinstance(self.options.get("entries"), str): self.options["entries"] = json.loads(self.options["entries"])`. Apply same pattern to `record_types` for symmetry. The same class of bug exists in `AddFieldsToPageLayout` (encountered while investigating #3613): `cci task run add_page_layout_fields ... -o fields '[...]'` -> `pydantic.ValidationError: value is not a valid list`. A more general fix would be a helper in the CLI/task-base that auto-parses JSON strings for list-typed options, or schema-driven coercion via the new task_options Pydantic models.

---

## Round 3 (2026-05-13 → 2026-05-14)

Themes: robotframework (subagent 13), scratch-org-config (subagent 14), auth (subagent 15), keychain (subagent 16), docs (subagent 17), python-modernization (subagent 18).
Scope: 17 issues across 6 themes, all against `origin/dev` @ `1925a3083` (NOT v4.10.0 like Rounds 1+2).
Verdicts: 12 REPRODUCED-on-dev, 5 NOT-REPRODUCED-on-dev. 10 `xfail` tests staged at `/tmp/repro/{13..18}/tests/`.

<!-- =============== R3 subagent 13 =============== -->

# Subagent 13 (rf) — Round 3 robotframework triage

Worktree: `.worktrees/repro-rf` (`worktree/repro/rf` @ `1925a3083` on `origin/dev`).

5 issues processed: #3955, #3873, #675, #987, #3602.

---

### #3955: Open Test Browser - SalesforcePlaywright.robot

**Verdict**: REPRODUCED-on-dev
**Repro type**: bug
**Method**: code-scan + pytest (mocked Browser library)

**Evidence**:

-   `cumulusci/robotframework/SalesforcePlaywright.py:106` — `width, height = size.split("x", 1)` returns two `str` values.
-   `cumulusci/robotframework/SalesforcePlaywright.py:109-111` — the strings are forwarded directly:

    ```python
    context_id = self.browser.new_context(
        viewport={"width": width, "height": height}, recordVideo=record_video
    )
    ```

-   Playwright contract requires `viewport.width` / `viewport.height` to be `int`, hence the runtime error `viewport.width: expected integer, got string` reported by the user (and confirmed by commenter @rasjani's pointer to lines 106-111).

**Proposed fix sketch**:

-   Approach: cast both fragments to `int` immediately after splitting.
-   Target: `cumulusci/robotframework/SalesforcePlaywright.py:106`
-   Size: small (~1 line) — e.g. `width, height = (int(v) for v in size.split("x", 1))`
-   Risk: low — preserves all existing call sites; users were already passing the documented `WxH` string format.
-   API break: no.

**Recommended action**:

-   pass1: `keep-open` — clear, low-risk, single-line bug fix; great good-first-issue candidate.
-   pass2 labels: `bug, robotframework, playwright, good-first-issue`
-   triage test: `cumulusci/tests/triage/test_issue_3955.py`

---

### #3873: Standalone Robot Framework Library for Selenium-Based Salesforce Automation (Inspired by Copado QForce)

**Verdict**: REPRODUCED-on-dev (feature still missing)
**Repro type**: feature
**Method**: code-scan

**Evidence**:

-   `cumulusci/robotframework/base_library.py:1-39` — `BaseLibrary` lazily resolves `cumulusci.robotframework.CumulusCI`, `cumulusci.robotframework.Salesforce`, `cumulusci.robotframework.SalesforceAPI` libraries through Robot's `BuiltIn`, which require a CumulusCI project context.
-   `cumulusci/robotframework/Salesforce.py:20-28` — imports `cumulusci.robotframework.locator_manager`, `faker_mixin`, `form_handlers`, plus the rest of the cci core that ships in the same package.
-   There is no standalone distribution; the Salesforce/SalesforcePlaywright libraries cannot be installed without the full `cumulusci` wheel and project layout.

**Proposed fix sketch**:

-   Approach: factor a UI-only subset out of `cumulusci.robotframework.*` into a sibling distribution (e.g. `salesforce-robot-library`) that depends only on Selenium/Playwright + the locator dictionaries; have CumulusCI's Robot task consume that subset.
-   Target: package layout change spanning `cumulusci/robotframework/` and `pyproject.toml`.
-   Size: large (>100 lines, design change + new distribution).
-   Risk: medium — must not break existing tasks/keywords.
-   API break: no (additive new distribution).

**Recommended action**:

-   pass1: `keep-open` — reasonable architectural request, age <24mo, no community PR yet; worth retaining as roadmap signal.
-   pass2 labels: `enhancement, robotframework, scope-large`
-   triage test: n/a — no concrete API to xfail against.

---

### #675: Show full traceback for Python exceptions in robot keywords

**Verdict**: REPRODUCED-on-dev (feature still missing)
**Repro type**: feature (cli-usability)
**Method**: code-scan

**Evidence**:

-   `cumulusci/tasks/robotframework/robotframework.py` configures listeners (`KeywordLogger`, `DebugListener`) but never sets `loglevel`/`logtitle`/`pythonpath` to surface Python tracebacks. `rg 'traceback|format_exc|format_tb' cumulusci/robotframework/` returns 0 matches; same for `cumulusci/tasks/robotframework/`.
-   Robot Framework's default behaviour: when a Python keyword raises, only `str(exc)` is shown in the report; the full traceback requires either `--loglevel TRACE`, `--listener` overrides, or `error.ROBOT_CONTINUE_ON_FAILURE`/`error.ROBOT_EXIT_ON_FAILURE` plumbing. CumulusCI does none of this by default.

**Proposed fix sketch**:

-   Approach: in `Robot._init_options`, default `options.loglevel` to include `TRACE`, OR install a small listener that captures `sys.exc_info()` in keyword-end events and emits a formatted traceback through `robot.api.logger.error`.
-   Target: `cumulusci/tasks/robotframework/robotframework.py:104` (`_init_options`).
-   Size: small (~10 lines).
-   Risk: low — additive listener; opt-out via options if needed.
-   API break: no.

**Recommended action**:

-   pass1: `closed:stale-24mo` — issue opened 2018-07, last activity 2018-09, ~8 years inactivity. Two simple workarounds exist (`-o loglevel:TRACE`, `traceback.format_exc()` in keywords). Surface as a tip in docs rather than keep the bug open.
-   pass2 labels: `cli-usability, robotframework, stale`
-   triage test: n/a — observable only in a robot run.

---

### #987: Last week this test worked, now I get a javascriptexception message.

**Verdict**: NOT-REPRODUCED-on-dev
**Repro type**: bug (legacy)
**Method**: code-scan + history review

**Evidence**:

-   Issue specifies Salesforce Spring 19, chromedriver 2.46.628411, chrome 72.0.3626.109 — all extinct.
-   Reporter posted on 2019-02-18: _"@davisagli I figured out a work-around. Use firefox with geckodriver. Everything works as intended now."_ — i.e. accepted a working alternative.
-   `cumulusci/robotframework/Salesforce.py:154` `click_object_button` still calls `_jsclick`, which has been the workaround pattern for shadow-DOM-aware clicks for years; current Selenium 4 / Salesforce Lightning UI no longer surfaces the original `Cannot read property 'defaultView' of undefined` error in the same form.
-   Last comment 2022-06 (davidmreed asking if still impacted; no response).

**Proposed fix sketch**: n/a — environment-specific historical bug.

**Recommended action**:

-   pass1: `closed:stale-24mo` — reporter has a workaround, root cause was Spring 19 specific, 7+ years stale, last activity 2022-06 (still 4 years ago).
-   pass2 labels: `stale, user-error`
-   triage test: n/a — would require a live 2019 org snapshot.

---

### #3602: Need Chrome/Firefox options(browser options/capabilities) in 'Open Test Browser' Keyword

**Verdict**: REPRODUCED-on-dev (feature still missing)
**Repro type**: feature
**Method**: code-scan + pytest (signature assertion)

**Evidence**:

-   `cumulusci/robotframework/SalesforcePlaywright.py:60-62` — `def open_test_browser(self, size=None, useralias=None, wait=True, record_video=None):` has no `browser_options`/`extra_options`/`**kwargs` hook.
-   `cumulusci/robotframework/Salesforce.robot:103` — Selenium keyword signature `[Arguments]  ${size}=...  ${alias}=${NONE}  ${wait}=True  ${useralias}=${NONE}` — same gap.
-   `cumulusci/robotframework/Salesforce.robot:157-168` `Get Chrome Options` hard-codes a single `--disable-notifications` argument with no extension hook.
-   Users cannot load Chrome extensions, switch to incognito, change download directory or accept self-signed certs without a fork of `Salesforce.robot`.

**Proposed fix sketch**:

-   Approach (Playwright): add a `browser_options: dict | None = None` kwarg; pass through to `new_browser` (browser-launch options) and a separate `context_options` dict merged into the `new_context` call.
-   Approach (Selenium): expose a `${EXTRA_CHROME_OPTIONS}` variable / list argument honoured by `Get Chrome Options`; alternatively add an `extra_options` argument to `Open Test Browser` and pipe through to `Create Webdriver With Retry`.
-   Target: `cumulusci/robotframework/SalesforcePlaywright.py:60-117`; `cumulusci/robotframework/Salesforce.robot:77-168`.
-   Size: medium (~30-60 lines across both implementations + tests + docs).
-   Risk: low — additive parameter with safe default.
-   API break: no (default `None` preserves current behaviour).

**Recommended action**:

-   pass1: `keep-open` — reasonable, scoped feature ask; age <36mo; no PR yet; tractable medium-sized contribution.
-   pass2 labels: `enhancement, robotframework, playwright, good-second-issue`
-   triage test: `cumulusci/tests/triage/test_issue_3602.py`

<!-- =============== R3 subagent 14 =============== -->

# Subagent 14 — scratch-org-config theme, Round 3

Working tree: `.worktrees/repro-scratch` on `worktree/repro/scratch` off `origin/dev` at `1925a3083`.

Triaged 3 issues (#3910, #3306, #710). All three remain actionable on dev: #3910 has an open fix PR; #3306 and #710 are never-implemented enhancements.

### #3910: JSON Schema incorrectly defines namespaced field as string instead of boolean for scratch org configuration

**Verdict:** `REPRODUCED-on-dev`. Bug.

**Evidence:**

-   `cumulusci/utils/yaml/cumulusci_yml.py:150` declares `namespaced: str = None` on the `ScratchOrg` Pydantic v1 model.
-   The auto-generated schema at `cumulusci/schema/cumulusci.jsonschema.json:424` reads `"type": "string"` (the test `cumulusci/tests/test_schema.py:test_schema_is_current` enforces that the saved schema matches the model output, so the two are locked together).
-   `ScratchOrg.parse_obj({"namespaced": True})` silently coerces to the literal string `"True"`; `{"namespaced": False}` to `"False"`. Either value is non-empty, so a downstream `if not self.namespaced` check would flip its logic if the model output were used directly.
-   The actual runtime path (`BaseProjectKeychain.create_scratch_org` at `cumulusci/core/keychain/base_project_keychain.py:74`, then `ScratchOrgConfig._build_org_create_args` at `cumulusci/core/config/scratch_org_config.py:143`) bypasses the Pydantic model via `project_config.lookup`, so booleans set in YAML survive at runtime. The user-visible impact is therefore: editors that consume the JSON schema reject `namespaced: true`/`false` (boolean) in `cumulusci.yml`, and `make schema` regenerates the same incorrect schema until the model is fixed.
-   Open PR [#3911](https://github.com/SFDO-Tooling/CumulusCI/pull/3911) (base `main`, branch `fix/namespaced-config-value-type-in-schema`) correctly fixes both files. State on 2026-05-14: OPEN, not merged.

**Repro test:** `/tmp/repro/14/tests/test_issue_3910.py` — 4 XFAILs against the schema JSON, the live Pydantic schema, and the model's coercion of booleans.

**Proposed fix sketch**

-   Approach: land PR #3911 essentially as-is (one-line Pydantic field change in `cumulusci_yml.py` + `make schema` regenerated `cumulusci.jsonschema.json`). Both edits must ship together because `test_schema_is_current` would otherwise fail.
-   Target file:line: `cumulusci/utils/yaml/cumulusci_yml.py:150` (`namespaced: str = None` → `namespaced: bool = None`); regenerate `cumulusci/schema/cumulusci.jsonschema.json`.
-   Size: small.
-   Risk: low. The only Pydantic consumers of `ScratchOrg.namespaced` are YAML-validation pathways; the runtime keychain path already uses booleans.
-   API break: no (silent coercion was incidental and arguably already broken for users).

### #3306: Preview Toggle for Scratch org def file

**Verdict:** `NOT-REPRODUCED-on-dev`. Feature.

**Evidence:**

-   `cci org scratch` already supports `--release preview|previous` (`cumulusci/cli/org.py:567-579`) and threads it through `BaseProjectKeychain.create_scratch_org` (`cumulusci/core/keychain/base_project_keychain.py:57-84`) to `ScratchOrgConfig._build_org_create_args` (`cumulusci/core/config/scratch_org_config.py:149-150`).
-   `cci flow run` (`cumulusci/cli/flow.py:119-200`) has no `--release` / `--preview` flag. The flow path also auto-recreates expired scratch orgs in `cumulusci/cli/runtime.py:106-114` without forwarding any release argument.
-   Internally tracked as W-11486409; no PR opened in 4 years.

No test written — this is a clean enhancement request whose API surface (`--preview` vs `--release` flag, behaviour with non-scratch orgs, behaviour when `release` is already set in YAML) is not yet specced.

### #710: Allow disabling default scratch org configs

**Verdict:** `REPRODUCED-on-dev`. Feature.

**Evidence:**

-   The universal config at `cumulusci/cumulusci.yml:1559` defines five default scratch orgs (`dev`, `qa`, `feature`, `beta`, `release`).
-   `BaseProjectKeychain._load_scratch_orgs` (`cumulusci/core/keychain/base_project_keychain.py:149-159`) iterates every key under `orgs.scratch` and calls `create_scratch_org` unconditionally.
-   `merge_config` (`cumulusci/core/utils.py:158`) calls `dictmerge`, which drops a `None` value from the project-side override (`{"orgs": {"scratch": {"dev": {"config_file": None}}}}` merged with the universal config still resolves to the universal's `config_file: orgs/dev.json`). The exact syntax proposed by the issue therefore has no effect.

**Repro test:** `/tmp/repro/14/tests/test_issue_710.py` — 2 XFAILs. One asserts that the project-side `config_file: None` override survives `merge_config`; the other asserts the resulting keychain does not load `dev`.

**Proposed fix sketch**

-   Approach: introduce a sentinel for "disabled" (recommend an explicit `disabled: true` flag on each scratch org config rather than relying on `config_file: None`, which has overloaded meaning) and skip disabled entries in `_load_scratch_orgs`. Optional: a stricter `merge_config` mode that preserves `None` overrides under `orgs.scratch.*`.
-   Target file:line: `cumulusci/utils/yaml/cumulusci_yml.py:147` (add `disabled: bool = None` to `ScratchOrg`); `cumulusci/core/keychain/base_project_keychain.py:155` (skip when `config.get("disabled")`); regenerate `cumulusci/schema/cumulusci.jsonschema.json`.
-   Size: small/medium.
-   Risk: low. Existing keys remain compatible; only adds new opt-in behaviour. Needs a docs note (`docs/orgs/scratch.md`) on how to disable inherited defaults.
-   API break: no (additive). The issue's literal `config_file: None` syntax would NOT be honoured under this proposal; if the team prefers that exact syntax instead, add a `dictmerge` exception so `None` overrides under `orgs.scratch.*` are preserved, then have `_load_scratch_orgs` skip entries with `config_file is None`. Either implementation satisfies the XFAIL test (`dev not in keychain.orgs`).

<!-- =============== R3 subagent 15 =============== -->

### #2667 — `cci org connect` should output the name of the connected app it is using

**Theme**: auth · **Bucket**: enhancement (cli-output) · **Verdict**: `NOT-REPRODUCED-on-dev`

**Original ask (prescod, 2021-06-08)**: When connecting an org, print which connected app is being used, e.g. `"Using connected_app 'xyzzy'"`, so users get a hint when a connected-app mismatch is the source of a confusing Salesforce error.

**Status on `origin/dev` @ `1925a3083`**: Implemented. `cumulusci/cli/org.py` `org_connect` resolves the connected-app name (CLI flag → keychain default) and emits, before initiating OAuth:

```204:209:cumulusci/cli/org.py
    click.echo(f"Connecting org using the {connected_app_name} connected app...")
    connected_app = runtime.keychain.get_service("connected_app", connected_app_name)
    sf_client = setup_client(connected_app, login_url, sandbox)
    connect_org_to_keychain(
        sf_client, runtime, global_org, org_name, connected_app_name
    )
```

The connected_app name is also persisted onto the new `OrgConfig` (`org_config.config["connected_app"] = connected_app`, line 155), addressing davisagli's follow-up that orgs should remember which connected app authorized them.

**Implementation history** (via `git log -L`):

-   `8fe1910b1` "refactor into separate methods" — split out `connect_org_to_keychain` and `setup_client`.
-   `40520bee4` "checkpoint" (2022-01-31) — introduced the `connected_app_name` resolution and the `click.echo` line. This is the commit that closes the loop on this issue. Matches davidmreed's 2022-01-28 comment "Covering in W-9863651".
-   `719d40260` "more tests, use the stored connected_app" — added test coverage and passed `connected_app_name` through to `connect_org_to_keychain` so it is stored on the org.

**Test coverage already present**:

-   `cumulusci/cli/tests/test_org.py::TestOrgCommands::test_org_connect` asserts `"Connecting org using the built-in connected app..." in result.output` (line 135).
-   `cumulusci/cli/tests/test_org.py::TestOrgCommands::test_org_connect__non_default_connected_app` asserts `"Connecting org using the other connected app..." in result.output` (line 191), explicitly covering the non-default case the issue called out as most important.

Both pass on dev (verified locally; 10/10 `test_org_connect*` tests pass).

**Recommendation**: `close-stale` with labels `resolved,implemented`. The exact phrasing differs from the issue's mock-up (`"Connecting org using the X connected app..."` vs `"Using connected_app 'X'"`), but the substantive ask — surfacing the connected-app identity at connection time — is satisfied. davisagli's deeper suggestions (configurable production/sandbox login URLs per connected app; auto-pick connected_app from login URL) are out of scope for this ticket and can be filed separately if still wanted.

<!-- =============== R3 subagent 16 =============== -->

# Subagent 16 (keychain) — Round 3 narrative

Worktree: `.worktrees/repro-keychain` @ `1925a3083` (off `origin/dev`).
Issues processed: 3/3 (#2126, #3407, #3541).
Verdict tally: 1 NOT-REPRODUCED (feature/stale), 2 REPRODUCED-on-dev.

### #2126 — Probabilistic-encryption task

**Classification**: feature request, theme-mismatched (Shield Platform
Encryption, not keychain).

**What dev shows**: no `encrypt_all_encryptable_fields` task exists.
`rg -i 'encryptionScheme|encrypt_all_encryptable|probabilistic' cumulusci/`
returns zero hits. The issue is labelled `blocked` since 2022-01-28 when
davidmreed wrote "this feature has been developed but is blocked by bugs in
the underlying platform functionality." No platform follow-up has surfaced
in the comments; the issue is 5+ years stale.

**Verdict**: `NOT-REPRODUCED-on-dev` (feature scope; no bug to reproduce).

**Pass-1 recommendation**: `closed:stale-24mo`. Pass-2 labels: `area/metadata-etl`,
`blocked` (theme correction). No fix sketch — close or hand off to the
metadata-ETL theme owner with a stale-feature ping.

### #3407 — `set_service(service_config)` annotation lies

**Classification**: typing/API-consistency bug, still present on dev.

**Reproduction path**:

-   `cumulusci/core/keychain/base_project_keychain.py` lines 202-209 declare
    `service_config: ServiceConfig` on `set_service`.
-   `cumulusci/core/keychain/encrypted_file_project_keychain.py` line 717
    calls `set_service(service_type, name, config, save=False, config_encrypted=True)`
    where `config` is the raw text body of a `.service` file read at line 712-713.
-   `_set_service` (encrypted_file_project_keychain.py:583-605) explicitly
    short-circuits when `self.key and config_encrypted` and treats
    `service_config` as the already-serialised payload, so the call is
    semantically correct — the annotation is what's wrong.

The two-test repro (`/tmp/repro/16/tests/test_issue_3407.py`) introspects the
annotation, confirms a string call site exists in `_load_service_files`, and
exercises the runtime path with a string payload via a `BaseProjectKeychain`
subclass. Both xfail on dev.

**Proposed fix sketch**

-   **Approach**: Widen the annotation. `set_service`'s `service_config`
    parameter should be `Union[ServiceConfig, str]` (or `ServiceConfig | str |
bytes`) and the docstring updated to say "raw encrypted payload when
    `config_encrypted=True`". The deeper refactor — splitting the API into
    `set_service` (validated `ServiceConfig`) and `set_encrypted_service`
    (raw blob) — is cleaner but breaks the public API and is out of scope
    for this triage pass.
-   **Target**: `cumulusci/core/keychain/base_project_keychain.py:202-219`.
    Also add the same widened annotation on the abstract `_set_service`
    (line 360) and propagate to `EncryptedFileProjectKeychain._set_service`
    (line 583).
-   **Size**: ~10 LOC plus a typing-import bump. Single-file change feasible.
-   **Risk**: very low. Pure type-hint widening; no runtime behaviour change.
    Downstream callers that already pass `ServiceConfig` keep working;
    pyright/mypy users gain an accurate hint.
-   **API break**: no. Widening a parameter type is non-breaking for
    callers.

### #3541 — `None__dev` SFDX alias

**Classification**: real bug, mis-labelled `cannot-reproduce`.

**Reproduction path**:

-   `cumulusci/core/keychain/base_project_keychain.py` lines 77-79:

    ```python
    scratch_config["sfdx_alias"] = (
        f"{self.project_config.project__name}__{org_name}"
    )
    ```

-   When `project_config.project__name` is None (cumulusci.yml without a
    `project.name`, or partially-loaded project_config), this f-string
    serialises the singleton `None` to the literal text `"None"`. The alias
    becomes `"None__dev"`.
-   Eager `_load_scratch_orgs` (line 45 → line 149-159) runs on keychain
    construction and creates these mis-aliased configs before the user ever
    runs `cci org scratch`. Reporter's claim that `cci org scratch dev dev`
    fixes it is consistent: the explicit call re-runs `create_scratch_org`
    after the project has fully loaded.
-   The poisoned alias is then passed to `sfdx force config set
target-org={alias}` at `base_project_keychain.py:99`, producing the
    reporter's symptom.

Two xfail tests in `/tmp/repro/16/tests/test_issue_3541.py` build a
`BaseProjectConfig` without `project.name`, drive both the direct
`create_scratch_org` path and the eager-init `_load_scratch_orgs` path, and
assert the resulting alias contains no literal `'None'` token. Both fail on
dev.

**Proposed fix sketch**

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

<!-- =============== R3 subagent 17 =============== -->

# Subagent 17 (docs) — Round 3 narrative

Worktree: `.worktrees/repro-docs` @ `1925a3083` (off `origin/dev`).
Issues processed: 3/3 (#773, #2500, #3464).
Verdict tally: 3 REPRODUCED-on-dev (all pure doc-gaps with code-level
testable assertions).

### #773 — Document task return values and results

**Classification**: feature-with-doc-component (needs a small framework
hook + matching renderer + the docs themselves).

**What dev shows**:

-   `BaseTask` (`cumulusci/core/tasks.py:51`) declares `return_values: dict`
    as an instance attribute (line 64), initialised to `{}` in `__init__`
    (line 92), populated at runtime by each task's `_run_task()`. There is
    no declarative class attribute that would describe the _shape_ of those
    return values.
-   `doc_task()` (`cumulusci/utils/__init__.py:354`) walks `task_options`
    and a free-form `task_docs` string and emits "Description", "Class",
    "Command Syntax", and "Options" sections. There is no "Return Values"
    or "Returns" section — and no plumbing to add one.
-   `cci task info <name>` is implemented by `cumulusci/cli/task.py:99`,
    which delegates straight to `doc_task`, so it has the same gap.
-   The docs themselves admit this. `docs/config.md:740-744` includes an
    `attention` admonition that reads: _"Current task return values are
    not documented, so finding return values set by a specific task (if
    any) requires you to read the source code for the given task."_

So 8 years after the issue was filed, the documented workaround in the
docs is still "read the source". The repro test (`/tmp/repro/17/tests/test_issue_773.py`)
runs `doc_task` against a real shipping task (`PackageUpload`, whose
`_set_return_values()` populates `version_number` / `version_id` /
`package_id`) and asserts the rendered RST mentions any of those keys.
It xfails today.

**Verdict**: `REPRODUCED-on-dev`.

**Proposed fix sketch**:

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

### #2500 — `ignore_failure` is not documented

**Classification**: pure doc-gap (the feature exists and works; only the
docs are missing).

**What dev shows**:

-   The option exists in three independent places, so it is a stable,
    public, supported feature:
    -   `cumulusci/utils/yaml/cumulusci_yml.py:45` — `Step` Pydantic model
        declares `ignore_failure: bool = False`.
    -   `cumulusci/core/flowrunner.py:667` — uses `step_config.get("ignore_failure", False)`
        to drive the `allow_failure` flag passed into the step runner.
    -   `cumulusci/schema/cumulusci.jsonschema.json:149` — exported in the
        JSON schema for IDE autocomplete.
-   In `docs/`, total mentions are exactly two: a single-line example use
    inside a release-flow snippet at `docs/config.md:800`
    (`ignore_failure: True`) and a one-line changelog blurb at
    `docs/history.md:5993` from when the feature shipped.
-   The `## Flow Configurations` chapter (line 294) has subsections for
    "Add a Custom Flow" (303), "Add a Flow Step" (330), "Skip a Flow Step"
    (388), "Replace a Flow Step" (414), "Configure Options on Tasks in
    Flows" (432) — and there is documentation prose for `when:` at line
    474+ — but no parallel subsection for `ignore_failure`.
-   Davidmreed cut GUS W-10908655 on 2022-03-28 to track it; nothing has
    landed in the 4+ years since.

The repro test (`/tmp/repro/17/tests/test_issue_2500.py`) confirms the
option exists in the `Step` model and asserts `docs/config.md` has a
heading-level section matching `ignore[ _]failure|ignore a failed|continue.*failure`.
The heading assertion xfails today; the existence assertion passes.

**Verdict**: `REPRODUCED-on-dev`.

**Proposed fix sketch**:

Add `### Ignore a Failed Step` (or `### Continue After a Failed Step`)
to `docs/config.md` immediately after the existing `### Skip a Flow Step`
section. Body should cover:

-   What it does: when `ignore_failure: True` is set on a step, an
    exception raised by that step does not abort the flow; subsequent
    steps still run.
-   A minimal YAML example (the existing `release_unlocked_production`
    snippet around line 783 already demonstrates it — link to it instead
    of duplicating).
-   Interaction with `^^step.return_value` references: downstream steps
    that reference a failed step's return values must defend against
    missing keys.
-   When NOT to use it: in CI, silently ignoring a failure hides
    regressions; prefer a `when:` clause for intentional conditional
    branching.
-   One sentence on the difference between `ignore_failure` (post hoc:
    swallow the exception) and `when:` (a priori: skip the step entirely).

This is a tiny, high-leverage docs PR — a strong candidate for a
`good-first-issue` label.

### #3464 — Concise project-config documentation

**Classification**: doc-gap with structural-fix implications (the most
sustainable fix changes how docs are generated, not just what they say).

**What dev shows**:

-   The authoritative shape of `project:` is the `Project` Pydantic model
    at `cumulusci/utils/yaml/cumulusci_yml.py:135`, with nine fields:
    `name`, `package`, `test`, `git`, `dependencies`,
    `dependency_resolutions`, `dependency_pins`, `source_format`, `custom`.
    Each of those (except scalars) points at a further sub-model with its
    own fields — `Package` has 7, `Git` has 10, `DependencyResolutions`
    has 3, `Test` has 1.
-   `docs/config.md` shows exactly one project-level YAML example at line
    281 (NPSP's `project` block) covering `name` + a partial `package`.
    There is no reference subsection enumerating every `project:` key.
-   Substring scans of `docs/config.md`:
    -   `dependency_resolutions` → 0 occurrences.
    -   `dependency_pins` → 0 occurrences.
    -   `source_format` → 6 occurrences, all inside flow-step `when:`
        clauses, not as a project-level reference.
    -   `custom` → 29 occurrences but none are about `project.custom`.
-   The keys that _are_ documented live in a separate page — `docs/dev.md`
    has `dependency_resolutions` at lines 596, 727 and `dependency_pins`
    at lines 499, 509, 535 — which is exactly the _"scattered to the
    wind"_ complaint in the issue body. jstvz acknowledged the gap in the
    one comment on the issue ("We've made improvements to the
    documentation over time, but there is still work to be done to make
    it easier for users to find what they need").

The repro test (`/tmp/repro/17/tests/test_issue_3464.py`) enumerates
every field of the `Project` Pydantic model and asserts each name
appears at least once in `docs/config.md`. Today it lists the missing
keys; xfails.

**Verdict**: `REPRODUCED-on-dev`.

**Proposed fix sketch**:

Two-step path:

1. **Tactical**: expand the `### Project Configurations` heading at
   `docs/config.md:673` into a real reference subsection that lists
   every `project:` top-level key with a one-sentence description and
   one example value. Cross-link to `docs/dev.md` for in-depth treatment
   of `dependencies` / `dependency_resolutions` / `dependency_pins` so
   we are not duplicating the longer narratives, just providing a
   central index. This alone closes the issue per the user's literal
   ask.

2. **Strategic** (separate, follow-up PR): backfill `Field(description=...)`
   on every Pydantic attribute in `cumulusci_yml.py` and add a Sphinx
   directive (or a `conf.py` autodoc hook) that emits the reference
   table directly from the model at docs-build time. This keeps the
   reference and the schema in lockstep — the same mechanism powers the
   JSON schema (`cumulusci/schema/cumulusci.jsonschema.json`), so the
   plumbing is straightforward.

Step 1 is a single-day effort; step 2 is multi-day but pays back every
time a new field is added to `cumulusci.yml`. Recommend keep-open until
at least step 1 ships.

<!-- =============== R3 subagent 18 =============== -->

# Subagent 18 (pymod) — Round 3 narrative

Worktree: `.worktrees/repro-pymod` @ `worktree/repro/pymod` based on `origin/dev` (`1925a3083`).

### #3849 — urllib3 v2 breaks Robot tests on a fresh pip install

**Verdict**: `REPRODUCED-on-dev` → `keep-open`.

**Code scan**:

-   `pyproject.toml` `[project].dependencies` (lines 26–59) declares no `urllib3` constraint. It still pins `selenium<4` (line 54) and `robotframework-seleniumlibrary<6` (line 50). Both of those pin chains force `selenium==3.141.0`, whose `urllib3` import-time use of the pre-2.0 `Timeout` sentinel object is what produces the user-reported `ValueError: Timeout value connect was <object object at 0x...>`.
-   `requests` (installed as a transitive runtime dep) declares `urllib3<3,>=1.26`, so a fresh `pip install cumulusci` resolves to whatever `urllib3` 2.x is current on PyPI. The local worktree happens to have `urllib3==1.26.20` because `uv sync` consumed `uv.lock`, but the lock is not what pip sees. Confirmed via `uv run python -c "import importlib.metadata as md; print(md.metadata('selenium').get_all('Requires-Dist'))"` → `selenium` declares `urllib3` with no version constraint.
-   `git log --all --grep urllib3` shows only dependabot lock bumps (e6423311e, 05a904856) that never landed on `dev`. The original 2018 fix referenced in `docs/history.md` (`#832`) is not reflected in the modern dependency list.
-   6+ users have reported reblocking on this in 2024–2025 (Szandor72, dipakparmar, atran-agentsync, JonnyPower, elizabethrichardson-uw, kg345); the documented workaround is still `pip install urllib3==1.26.20` after installing cumulusci.

**Repro test**: `/tmp/repro/18/tests/test_issue_3849.py` parses the worktree's `pyproject.toml` (located via `cumulusci.__file__`) and asserts the modernized state — either an explicit `urllib3<…` constraint OR removal of both the `selenium<4` and `robotframework-seleniumlibrary<6` pins. Verified `XFAIL` under `uv run pytest -v -rx` (reason surfaces the docs path).

**Proposed fix sketch**: Two acceptable shapes.

1. **Cheap, restores Robot reliability**: add `"urllib3<2"` to `[project].dependencies` in `pyproject.toml`. This makes pip honor what `uv.lock` already encodes. Drop the matching workaround note from #3849.
2. **Right long-term**: bump to `robotframework-seleniumlibrary>=6` and `selenium>=4`, which removes the Timeout-sentinel incompatibility entirely. Audit `cumulusci/robotframework/*` for Selenium 4 API drift (the comment on the original PR notes integration tests caught urllib3 issues last time). The two pin entries on lines 50 and 54 of `pyproject.toml` are the visible footgun.

Either way, add a smoke test that imports `SeleniumLibrary` after a fresh resolve to keep the regression caught.

### #3610 — `run_tests` crashes when `ApexTestResult.MethodName` is null

**Verdict**: `NOT-REPRODUCED-on-dev` → `closed:fixed-by-pr-#3681`.

**Code scan**:

-   The original issue points at `cumulusci/tasks/apex/testrunner.py` L417 (sort that explodes on `None`) and L346–348 (dict keyed by `MethodName`). On `origin/dev` today the same module's `_process_test_results` (lines 491–510) explicitly handles `None`:

```500:510:cumulusci/tasks/apex/testrunner.py
            if None in method_names:
                class_id = self.classes_by_name[class_name]
                self.retry_details.setdefault(class_id, []).append(
                    self._get_test_methods_for_class(class_name)
                )
                del self.results_by_class_name[class_name][None]
                self.logger.info(
                    f"Retrying class with id: {class_id} name:{class_name} due to `None` methodname"
                )
                self.counts["Retriable"] += len(self.retry_details[class_id])
                self._attempt_retries()
```

-   This landed in PR #3681 / commit `84389d998b4783ddd2ff062f486a2366709cac27` (“Handling exception when the Tooling API returns a test result with a null method name”), with regression coverage in `cumulusci/tasks/apex/tests/test_apex_tasks.py::test_run_task_None_methodname_fail` and `…_pass`. Both pass on this worktree (`uv run pytest cumulusci/tasks/apex/tests/test_apex_tasks.py -k None_methodname -v` → `2 passed`).

No repro test added — the fix is in place and already has direct unit coverage. Closing the issue is a paperwork action.

**Proposed fix sketch**: none required. Recommend closing #3610 with a comment that points at PR #3681 and the two `None_methodname` tests.
