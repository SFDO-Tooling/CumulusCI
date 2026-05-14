# Fix sketch - #3754: Enable configuration for cci version update sources **Verdict**: `REPRODUCED-on-v4.10.0` (verdict_source: `v4.10.0`)

**Theme**: `cli`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3754> ## Bug - `cumulusci/cli/utils.py:65-79` - `get_latest_final_version` hits `https://pypi.org/pypi/cumulusci/json` literally, no env-var, no kwarg. - `cumulusci/cli/utils.py:82-101` - `check_latest_version` cannot be disabled via flag/env. Workaround in the comments (touch `~/.cumulusci/cumulus_timestamp` to a far-future epoch) confirmed by inspecting the timestamp logic at lines 38-50, 86-89. ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) - pass1: `keep-open` - easy add (e.g. `CUMULUSCI_DISABLE_VERSION_CHECK` env), helps offline/restricted environments.

-   | pass2 labels: `enhancement, area:cli` ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ---------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                        | _TBD by fix-PR author_ |
    | Risk                                                 | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                 | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                 | _TBD_                  |
    | Breaks public CLI surface                            | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3754.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3754:`). |
