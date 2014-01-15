# Job: Cumulus_uat
[See it in action](http://ci.salesforcefoundation.org/view/uat)

## Overview

The Cumulus_uat job is the first step in releasing a managed beta version of Cumulus.  The job is triggered by the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/) application similar to the [Cumulus_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_feature.md).  Whenever a tag is created in the repository starting with `uat/`, a build is triggered to deploy the tag to the cumulus.rel packaging org and run all tests.

## Target Org

Since the purpose of this job is to test the code and then prepare it for packaging into a managed beta version, the job runs against cumulus.rel, the Cumulus packaging org.

## Configuration

### Parameters

The build needs to know which tag to deploy and who to notify.  The parameters `branch` and `email` are passed by the trigger.

### Source Code Management

We want to build the specific tag provided by the `branch` parameter

### Build Triggers

This build is triggered remotely by the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/) app using an authenticated call to the Jenkins API.  Since the call is authenticated, we don't need to enable any job triggers.

### Build Environment

We set a custom build name so we know which tag was built rather than just a simple build number.

### Build

We use the updateDependentPackages target to update any of the original NPSP managed packages which need to be upgraded.  Since we're working against the packaging org, we can't clean the org as in other builds.  This configuration assumes there will never be a need to downgrade an NPSP package with a release.

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the developer who created the tag.

The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

Trigger a parameterized build of (Cumulus_uat_cinnamon_deploy)[https://github.com/SalesforceFoundation/CumulusCI/docs/jobs/Cumulus_uat_cinnamon_deploy] if the build is successful.

![Cumulus_uat - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_uat.png)
