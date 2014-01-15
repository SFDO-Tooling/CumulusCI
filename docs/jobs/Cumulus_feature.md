# Job: Cumulus_feature
[See it in action](http://ci.salesforcefoundation.org/view/feature)

## Overview

The Cumulus_feature job tests feature branches after each push to the Github repository.  It uses the *deployCI* target to first clean the org of all Cumulus metadata, then ensures all managed packages are at the correct version, and finally deploys the Cumulus package from the repository running all apex tests.  If any tests fail, the developer who made the last commit in the push is notified by email.  

This job is parameterized and expects the `branch` and `email` parameters to be passed so it knows which branch to build and who to notify if build fails.

Since this job is mostly a tool to help developers, the notification email on build failure is sent to the GitHub user who last pushed a commit to the branch.

Another alternative to this approach would be to build individual jobs for each feature branch.  This option was considered but we opted to use a single job to avoid the overhead of ensuring jobs are created and deleted when feature branches are created or deleted.  Also, in the Force.com context, you would either have to create a target org for each feature branch's job or add additional configuraiton to ensure multiple separate jobs don't run against the same target org.

## Target Org

This job uses an org dedicated to the job.  The org can be a Developer Edition or Partner Developer Edition instance and requires no up front configuration.  Thus, if an issue is encountered with an org, a new one can be created and easily linked to the job.

## Configuration

### Parameters

This job expects the `branch` and `email` parameters to be passed by the build trigger.  The trigger is sent by the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/) app running on Heroku which receives GitHub web hooks whenver a push is made to the repository.  We don't want to use any triggers directly from GitHub in Jenkins since the external app provides the trigger with needed parameters.

### Source Code Management

We use the `branch` parameter to tell the job which branch to checkout from GitHub

### Build Environment

We use the build-name-setter Jenkins plugin to name the builds after the feature branch

### Triggers

Since this job is triggered by the remote [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere/) app running on Heroku which uses an authenticated call to the Jenkins API, we don't need to enable any triggers on the job.

### Build

We use the default ant version and the deployCI ant target from the checked out branch to control the build.  The -propertyfile ../build.properities.cumulus.feat contains the credentials for the target org dedicated to this job.  The file should be located in the root of the Jenkins workspace or the path adjusted.

### Post Build

The Editable Email Notification post build action is used to send a formatted email to the developer who committed the last commit in the push.

The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

![Cumulus_feature - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_feature.png)
