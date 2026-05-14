# Fix sketch - #3407: `set_service(service_config)` annotation lies **Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `keychain`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3407> ## Bug - `cumulusci/core/keychain/base_project_keychain.py` lines 202-209 declare `service_config: ServiceConfig` on `set_service`. - `cumulusci/core/keychain/encrypted_file_project_keychain.py` line 717 ## Target `cumulusci/core/keychain/base_project_keychain.py:202-219`. Also add the same widened annotation on the abstract `_set_service` (line 360) and propagate to `EncryptedFileProjectKeychain._set_service` (line 583). ## Recommended approach (from triage narrative) - **Approach**: Widen the annotation. `set_service`'s `service_config` parameter should be `Union[ServiceConfig, str]` (or `ServiceConfig | str |
bytes`) and the docstring updated to say "raw encrypted payload when `config_encrypted=True`". The deeper refactor - splitting the API into `set_service` (validated `ServiceConfig`) and `set_encrypted_service` (raw blob) - is cleaner but breaks the public API and is out of scope for this triage pass.

-   **Target**: `cumulusci/core/keychain/base_project_keychain.py:202-219`. Also add the same widened annotation on the abstract `_set_service` (line 360) and propagate to `EncryptedFileProjectKeychain._set_service` (line 583).
-   **Size**: ~10 LOC plus a typing-import bump. Single-file change feasible.
-   **Risk**: very low. Pure type-hint widening; no runtime behaviour change. Downstream callers that already pass `ServiceConfig` keep working; pyright/mypy users gain an accurate hint.
-   | **API break**: no. Widening a parameter type is non-breaking for callers. ## Size & risk | Field                  | Value                                                                                                                                                                                                        |
    | ---------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
    | Size estimate                                                                            | _TBD by fix-PR author_ |
    | Risk                                                                                     | _TBD by fix-PR author_ |
    | Touches `cumulusci/robotframework/*`                                                     | _TBD_                  |
    | Touches `cumulusci/tasks/bulkdata/*`                                                     | _TBD_                  |
    | Breaks public CLI surface                                                                | _TBD_                  | ## Regression test `cumulusci/tests/triage/test_issue_3407.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3407:`). |
