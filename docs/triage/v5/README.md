# CCI v5 Issue Triage Evidence (May 2026)

This directory contains the results of an AI-assisted triage of the 142
open issues in `SFDO-Tooling/CumulusCI` as part of preparation for
CumulusCI v5.

## Contents

| File                         | Purpose                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------- |
| `README.md`                  | This file.                                                                                  |
| `proposals.md`               | Per-issue classification + proposed pass-1 action (kept-open, close-with-reason, etc.).     |
| `repro-results.md`           | Per-issue narrative evidence for the 115 issues that went through the reproducibility pass. |
| `repro-results.csv`          | Machine-readable matrix backing the narrative (one row per issue).                          |
| `themes.md`                  | Theme clusters, duplicate detection, and Tranche-1 candidate list.                          |
| `fix-sketches/issue_NNNN.md` | One fix sketch per `REPRODUCED` issue not slated for an immediate fix-PR.                   |

## Methodology

1.  **Classification**: All 142 open issues were evaluated against a
    hygiene policy covering staleness (>24mo no activity), missing
    reproducer information, and known-resolved status. Output:
    `proposals.md`.

2.  **Theme clustering**: Issues were grouped into 12 themes
    (`packaging`, `metadata-etl`, `cli`, `bulkdata`, `dependencies`,
    `ci-integration`, `robotframework`, `scratch-org-config`, `auth`,
    `keychain`, `docs`, `python-modernization`) with cross-theme
    duplicate detection. Output: `themes.md`.

3.  **Reproducibility pass**: 115 of 142 issues were verified in
    isolated git worktrees against CumulusCI v4.10.0 or `origin/dev`.
    The 27 `closed:pre-v4.0.0` issues were excluded from the repro pass
    (they're tagged separately for close). Verdicts:

    | Verdict                            |   Count |
    | ---------------------------------- | ------: |
    | `REPRODUCED-on-v4.10.0`            |      56 |
    | `REPRODUCED-on-dev`                |      24 |
    | `NOT-REPRODUCED-on-v4.10.0`        |      18 |
    | `NOT-REPRODUCED-on-dev`            |       5 |
    | `INCONCLUSIVE-needs-*` (kept-open) |      11 |
    | `closed:duplicate-of-#3544`        |       1 |
    | **Total**                          | **115** |

    Output: `repro-results.md`, `repro-results.csv`.

4.  **Failing-test capture**: For each `REPRODUCED-on-*` issue with a
    code-level assertion target, a `@pytest.mark.xfail(strict=False)`
    regression test was committed to `cumulusci/tests/triage/`. The
    xfail marker is intentionally non-strict so a bug that resolves
    independently surfaces as `XPASS` rather than as a CI failure.
    Fix-PRs remove the marker.

5.  **Fix sketches**: For every `REPRODUCED` issue not slated for an
    immediate fix-PR, `fix-sketches/issue_NNNN.md` captures the
    proposed approach, target `file:line`, size estimate, and risk.

6.  **Tranche 1 fix PRs**: A small slate of recent regressions
    (`#3852`, `#3854`, `#3886`, `#3938`, `#3939`) receives immediate
    fix-PRs against `dev` with the xfail marker removed and a
    corresponding passing unit test.

## AI assistance disclosure

This triage was conducted with AI assistance. Specifically:

-   Initial classification, theme clustering, and reproducibility
    verification were performed by AI coding agents working in
    isolated `git` worktrees with hard-coded constraints: no source
    mutation outside scope, no live-org access, no scratch-org
    creation outside a designated DevHub, no GitHub state mutation,
    no `git push`.
-   The xfail tests in `cumulusci/tests/triage/` are intentionally
    `strict=False`; an `XPASS` surfaces a verdict that no longer
    holds (e.g. the bug was fixed independently) rather than crashing
    CI.
-   All proposed pass-1 mutations against GitHub issues (close /
    label) are gated on explicit maintainer approval before
    execution. They are NOT executed by this PR.

Intermediate run logs (dispatch records, anomaly notes, consolidation
scripts) are kept locally and intentionally not included here.

## Spec basis

Pass-1 vocabulary used in `proposals.md`:

-   `closed:stale-24mo` - no activity >24 months, no maintainer label.
-   `closed:pre-v4.0.0` - body declares CumulusCI 3.x; no reporter
    reconfirmation against v4+.
-   `closed:missing-fields` - issue lacks repro / cci-version /
    expected behaviour.
-   `closed:pr-resolved-#NNNN` - fix already on dev via specified PR.
-   `closed:not-reproducible-on-v4.10.0` - bug not reproducible on
    v4.10.0; close with explicit verdict.
-   `closed:not-reproducible-on-dev` - bug not reproducible on `dev`;
    close with explicit verdict.
-   `closed:feature-implemented` - feature ask already shipped.
-   `closed:duplicate-of-#NNNN` - pointer to canonical issue.
-   `closed:pr-pending-#NNNN` - fix exists in an open PR ready to
    land; close once that PR merges.
-   `kept-open` - confirmed REPRO; rescue from close.

Pass-2 vocabulary (selected): `target:v4-patch`, `v5-candidate:yes|no`,
`severity:{critical,major,minor,trivial}`, `area:{packaging,bulkdata,
cli,robotframework,...}`.

## Tranche 1 candidate list

Recent regressions slated for immediate fix-PR against `dev`:

| Issue | Title                                                        | Estimated diff |
| ----- | ------------------------------------------------------------ | -------------- |
| #3852 | sarge cosmetic warning under Python 3.13                     | ~5-15 LOC      |
| #3854 | extract-validation regression from PR #3741                  | ~5-10 LOC      |
| #3886 | `cumulusci[select]` warning fires at every `extract_dataset` | ~3-5 LOC       |
| #3938 | (see fix-sketches/issue_3938.md)                             | TBD            |
| #3939 | (see fix-sketches/issue_3939.md)                             | TBD            |

Two adjacent fix-already-on-dev issues that close without a fix-PR
needed here:

-   `#3610` → `closed:pr-resolved-#3681` (already on dev).
-   `#3910` → `closed:pr-pending-#3911` (PR #3911 ready to land).
