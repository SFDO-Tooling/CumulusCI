# Job: Cumulus_feature

## Overview

The Cumulus_feature job tests feature branches after each push to the Github repository.  It uses the *deployCI* target to first clean the org of all Cumulus metadata, then ensures all managed packages are at the correct version, and finally deploys the Cumulus package from the repository running all apex tests.  If any tests fail, the developer who made the last commit in the push is notified by email.  

This job is parameterized and expects the BRANCH and EMAIL parameters to be passed so it knows which branch to build and who to notify if build fails.

## Target Org

This job uses an org dedicated to the job.  The org can be a Developer Edition or Partner Developer Edition instance and requires no up front configuration.  Thus, if an issue is encountered with an org, a new one can be created and linked to the job.

## Configuration

### Title and Description

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-title.png)

### Parameters

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-params.png)

### Source Code Management

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-scm.png)

### Build Environment

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-build_environment.png)

### Triggers

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-triggers.png)

### Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-build.png)

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the developer who committed the last commit in the push.

The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_feature-post_build.png)
