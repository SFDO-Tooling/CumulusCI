# Job: Cumulus_uat

## Overview

The Cumulus_uat job is the first step in releasing a managed beta version of Cumulus.  The job is triggered by the mrbelvedere application similar to the [Cumulus_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/).  Whenever a tag is created in the repository starting with `uat/`, a build is triggered to deploy the tag to the cumulus.rel packaging org and run all tests.

## Target Org

Since the purpose of this job is to test the code and then prepare it for packaging into a managed beta version, the job runs against cumulus.rel, the Cumulus packaging org.

## Configuration

### Title and Description

![Cumulus_uat - Title and Description](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-title.png)

### Parameters

The build needs to know which tag to deploy and who to notify.  The parameters `branch` and `email` are passed by the trigger.

![Cumulus_uat - Parameters](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-params.png)

### Source Code Management

We want to build the specific tag provided by the `branch` parameter

![Cumulus_uat - SCM](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-scm.png)

### Build Environment

We set a custom build name so we know which tag was built rather than just a simple build number.

![Cumulus_uat - Build Environment](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-build_environment.png)

### Triggers

The build needs to be configured to trigger remotely so mrbelvedere can trigger it when a new tag is created in GitHub.

![Cumulus_uat - Triggers](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-triggers.png)

### Build

We use the standard deployCI build target.

![Cumulus_uat - Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-build.png)

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the developer who created the tag.

The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

![Cumulus_uat - Post Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-post_build.png)
