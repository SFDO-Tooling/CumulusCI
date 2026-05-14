# Fix sketch - #3464: Concise project-config documentation **Verdict**: `REPRODUCED-on-dev` (verdict_source: `dev`)

**Theme**: `docs`
**Issue**: <https://github.com/SFDO-Tooling/CumulusCI/issues/3464> ## Bug Concise project-config documentation ## Target _See narrative for target file:line._ ## Recommended approach (from triage narrative) Two-step path: 1. **Tactical**: expand the `### Project Configurations` heading at `docs/config.md:673` into a real reference subsection that lists every `project:` top-level key with a one-sentence description and one example value. Cross-link to `docs/dev.md` for in-depth treatment of `dependencies` / `dependency_resolutions` / `dependency_pins` so we are not duplicating the longer narratives, just providing a central index. This alone closes the issue per the user's literal ask. 2. **Strategic** (separate, follow-up PR): backfill `Field(description=...)` on every Pydantic attribute in `cumulusci_yml.py` and add a Sphinx directive (or a `conf.py` autodoc hook) that emits the reference table directly from the model at docs-build time. This keeps the reference and the schema in lockstep - the same mechanism powers the JSON schema (`cumulusci/schema/cumulusci.jsonschema.json`), so the plumbing is straightforward. Step 1 is a single-day effort; step 2 is multi-day but pays back every
time a new field is added to `cumulusci.yml`. Recommend keep-open until
at least step 1 ships. Worktree: the triage worktree @ the triage worktree based on `origin/dev` (`1925a3083`). ## Size & risk | Field | Value |
| ------------------------------------ | ---------------------- |
| Size estimate | _TBD by fix-PR author_ |
| Risk | _TBD by fix-PR author_ |
| Touches `cumulusci/robotframework/*` | _TBD_ |
| Touches `cumulusci/tasks/bulkdata/*` | _TBD_ |
| Breaks public CLI surface | _TBD_ | ## Regression test `cumulusci/tests/triage/test_issue_3464.py`. Remove the `@pytest.mark.xfail` marker and confirm green. ## Full narrative See `docs/triage/v5/repro-results.md` (search for `### #3464:`).
