# Job: Cumulus_uat_cinnamon_deploy
[See it in action](http://ci.salesforcefoundation.org/view/uat)

## Overview

The Cumulus_uat_cinnamon_deploy is the first job of two involved in executing browser based tests through SauceLabs using Cinnamon.  This job is responsible for deploying the Cumulus UAT code to the cumulus.uat.cin org and then kicking off the [Cumulus_uat_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_test.md) build to run the Cinnamon tests.

## Target Org

This job runs against the dedicated cumulus.dev.cin org which has Cinnamon installed and configured manually outside of the build process.

## Configuration

### Parameters

The build needs to know which tag to deploy and who to notify.  The parameters `branch` and `email` are passed by the trigger.

### Source Code Management

We want to build the specific tag provided by the `branch` parameter

### Build Triggers

This job is triggered after a successful build of [Cumulus_uat](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat.md).

### Build Environment

We set a custom build name so we know which tag was built rather than just a simple build number.

### Build

We use the updateDependentPackages target to update any of the original NPSP managed packages which need to be upgraded.  Since we're working against the packaging org, we can't clean the org as in other builds.  This configuration assumes there will never be a need to downgrade an NPSP package with a release.

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the developer who created the tag if the build fails (Failure) or recovers from a failure (Fixed).

The *Set build status on GitHub commit* post build action flags the GitHub commit.

Trigger a parameterized build of [Cumulus_uat_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/docs/jobs/Cumulus_uat_cinnamon_test) if the build is successful.

![Cumulus_uat_cinnamon_deploy - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_uat_cinnamon_deploy.png)
