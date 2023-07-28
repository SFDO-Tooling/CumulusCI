---
date: 2023-07-28
status: Accepted
author: "@jstvz"
---

# ADR 2: Handling Migration from SFDX to SF CLI in CumulusCI

## Context and Problem Statement

## Context

Salesforce has announced the deprecation of SFDX (v7) and is now focusing on the newer SF CLI (v2). They've said that SF CLI (v2) is smart enough to understand all SFDX commands, as well as new SF commands. However, our web applications and other integrations depend on SFDX. SFDX is end-of-life, so we need to cut over and make some improvements by using the new, better features.

## Decision

### Considered Options

1. **Run commands based on what the user has (SFDX or SF CLI):**

    - Good: Gives users still using SFDX more time to switch.
    - Good: Gives us time to fully understand the new SF CLI.
    - Bad: It would make our code more complex and might confuse users.
    - Bad: It divides our attention between old and new versions.

2. **Stop supporting SFDX right away:**

    - Good: Lets us focus on the new SF CLI and stop worrying about old code.
    - Good: Speeds up our switch to the new CLI and helps us find and fix problems sooner.
    - Bad: It could disrupt users' work if they're still using SFDX.
    - Bad: There could be problems with the new SF CLI we don't know about yet.

3. **Let SF CLI handle old SFDX commands:**
    - Good: Reduces changes to our commands, making the switch smoother for users.
    - Good: Lets us switch to the new CLI slowly, reducing risk of big issues.
    - Bad: Delays the inevitable. If they drop deprecated commands without us noticing, it would break functionality for our users.
    - Bad: Could delay us learning and using new features of the SF CLI.

### Decision Outcome

Here's how we plan to make this change:

-   **Maintain Backwards Compatibility:** Our priority is to ensure that all existing processes continue to function as expected. We will not modify the existing SFDX commands in our project until SF CLI announces the version in which these commands will be deprecated.

-   **Delegate maintaining backwards compatibility to the SF CLI:** We will continue using existing commands as written and rely on SF CLI to interpret these commands. We think this will make the change easier and less disruptive.

-   **Warn users that are on SFDX (v7) that they need to upgrade:** We'll check the installed version of the CLI and warn users that future versions of CumulusCI will drop support.

-   **Update our integration tests to include `stable-rc`:** We'll revisit PR #3558 to make sure all tasks that use the CLI are tested in our workflow, and that we're testing the weekly release candidate channel (`stable-rc`).

-   **Update the Falcon web applications to depend on SF as soon as practical:** We know we need to switch to SF CLI, and we want our Falcon web apps to benefit from its latest updates and features as soon as possible. We'll also install all necessary JIT plugins in the apps, so we don't have to install them over and over during builds.

-   **Update the SFDX Heroku buildpack to depend on SF as soon as practical:** Like the Falcon web applications, we want our [Heroku buildpack](https://github.com/SalesforceFoundation/simple-salesforce-dx-buildpack)to stay up-to-date with the latest SF CLI to get its performance and feature enhancements. Like the Falcon web applications, this includes installing all necessary JIT plugins for the buildpack.

## Consequences

-   Keeping things working as they are will cause the least disruption.
-   By delegating backwards compatibility to the SF CLI, we can avoid making substantial changes to our command structure until it's necessary.
-   Updating Falcon web apps and the SFDX Heroku buildpack to use the SF CLI will help us stay ahead of the change and avoid a scramble as the CLI removes deprecated commands.
-   Installing JIT plugins in the apps and buildpack will make builds more efficient and avoid problems during runtime.
-   However, this decision does mean that we will need to monitor Salesforce's communications closely for announcements about command deprecations, to ensure that our commands continue to function as expected.

## References

-   [List of JIT plugins in SF CLI](https://github.com/salesforcecli/cli/blob/486a157c3d448d699c129f884bb3ab706523002a/package.json#L71-L81)
-   [Salesforce CLI sf (v2) announcement blog post](https://developer.salesforce.com/blogs/2023/07/salesforce-cli-sf-v2-is-here)
-   [CLI Deprecation Policy](https://developer.salesforce.com/docs/atlas.en-us.sfdx_setup.meta/sfdx_setup/sfdx_dev_cli_deprecation.htm)
-   [Issue #3621](https://github.com/SFDO-Tooling/CumulusCI/issues/3621)

<!--
## Notes

Notes and issues captured from team discussions.

Optional sections END-->
