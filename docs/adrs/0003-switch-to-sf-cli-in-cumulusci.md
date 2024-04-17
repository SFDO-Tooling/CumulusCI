---
date: 2023-12-04
status: Accepted
author: "@jstvz"
---

# ADR 3: Switching to SF CLI in CumulusCI

## Context and Problem Statement

Salesforce has deprecated SFDX (v7) in favor of the newer SF CLI (v2). Our web applications and other integrations currently depend on SFDX. To leverage new features and ensure support, we need to transition to SF CLI.

## Decision

### Considered Options

1. **Support Both SFDX and SF CLI:**

    - Good: Provides flexibility for users still on SFDX.
    - Good: Gives us time to fully understand the new SF CLI.
    - Bad: Increases code complexity and could lead to inconsistent behavior.

2. **Immediately Drop SFDX Support:**

    - Good: Lets us focus on the new SF CLI and stop worrying about old code.
    - Good: Speeds up our switch to the new CLI and helps us find and fix problems sooner.
    - Good: Gives us the opportunity to improve integration with the SF CLI.
    - Bad: It could disrupt users' work if they're still using SFDX.
    - Bad: There could be problems with the new SF CLI we don't know about yet.

3. **Delegate SFDX Command Handling to SF CLI:**
    - Good: Offers a smoother transition.
    - Bad: Could delay adoption of new SF CLI features.

### Decision Outcome

We will make a decisive switch to the SF CLI:

-   **Discontinue SFDX Command Use:** We will replace all SFDX commands in CumulusCI with their SF CLI equivalents. This shift ensures that we are using supported and up-to-date tools.

-   **Update Integration Tests:** Our tests will be updated to reflect this change. We will ensure that all tasks are compatible with the SF CLI.

-   **Update Web Applications and Heroku Buildpack:** Our Falcon web applications and the Heroku buildpack will be updated to depend solely on the SF CLI. We will ensure that all necessary JIT plugins are pre-installed.

-   **Direct Warning to SFDX Users:** A warning will be issued to users who are still on SFDX, informing them of the need to upgrade to the SF CLI.

## Consequences

-   This approach ensures that we are aligned with the latest Salesforce development tools and standards.
-   Immediate transition may require rapid adaptation but ensures future-proofing and access to the latest features.
-   Users of SFDX will need to upgrade, which may require some adjustment.
-   Our codebase will be simplified by focusing on a single CLI tool.
-   Installing JIT plugins in the apps and buildpack will make builds more efficient and avoid problems during runtime.

## References

-   [List of JIT plugins in SF CLI](https://github.com/salesforcecli/cli/blob/486a157c3d448d699c129f884bb3ab706523002a/package.json#L71-L81)
-   [Salesforce CLI sf (v2) announcement blog post](https://developer.salesforce.com/blogs/2023/07/salesforce-cli-sf-v2-is-here)
-   [CLI Deprecation Policy](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_dev_cli_deprecation.htm)
-   [Issue #3621](https://github.com/SFDO-Tooling/CumulusCI/issues/3621)

<!--
## Notes

Notes and issues captured from team discussions.

Optional sections END-->
