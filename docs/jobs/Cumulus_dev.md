# Job: Cumulus_dev
[See it in action](http://ci.salesforcefoundation.org/view/dev)

## Overview

The Cumulus_dev job runs after each commit to the repository and at scheduled times to ensure the dev branch passes all Apex tests.

## Target Org

This job uses a dedicated target org, cumulus.dev, to run its tests.

## Configuration

### Source Code Management

This job uses only the `dev` branch of the main Cumulus repository.

### Triggers

This job is triggered both by any commit to the `dev` branch and by a set schedule.  The scheduled builds occur every morning with extra builds scheduled around the start and end of month to catch date specific test failures.

### Build

The build uses the deployCI target to run a full clean, update, deploy, and test build against the cumulus.dev org.

### Post Build

If the build passes, we kick off a build of [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature.md)

The Editable Email Notification post build action is used to send a formatted email to all developers on failure (Failure) and recovery (Fixed).

The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

![Cumulus_dev - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_dev.png)
