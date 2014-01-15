# Job: Cumulus_rel
[See it in action](http://ci.salesforcefoundation.org/view/rel)

## Overview

This job is triggered by the creation of a tag prefixed with rel/ (i.e. rel/1.2).  It deploys the release tag code to the cumulus.rel org to allow for packaging into a managed package release.

## Target Org

This job runs against the cumulus.rel org which is the package org for Cumulus.

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

![Cumulus_rel - Post Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_rel.png)
