# Job: Cumulus_dev_cinnamon_deploy

## Overview

When the [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev.md) job completes, it kicks off Cumulus_dev_cinnamon_deploy.  This job is responsible for deploying the dev branch to the dedicated org for running Cinnamon tests against the dev branch.  Once the deployment completes, it kicks off the Cumulus_dev_cinnamon_test job to actually run the Cinnamon tests.

Cinnamon is a framework for using Apex to execute Selenium browser based tests for UI functionality which can't be fully tested via Apex.  The Salesforce.com Foundation is a pilot user of the new framework.  Thus, these instructions are not portable to other projects at this point in time but are documented here for future use if/when the package is available.

## Target Org

Since Cinnamon requires the installation of additional managed packages not required by Cumulus, we use a dedicated org to run the Cinnamon tests.  We refer to this org as cumulus.dev.cin

## Configuration

### Title and Description

![Cumulus_dev_cinnamon_deploy - Title and Description](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-title.png)

### Source Code Management

We store our Cinnamon tests in a dedicated repository so they can be deployed separately and avoid the risk of them getting bundled into the Cumulus package.

![Cumulus_dev_cinnamon_deploy - SCM](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-scm.png)

### Build

We use a shell script to kick off the Cinnamon command line client, ccli

![Cumulus_dev_cinnamon_deploy - Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-build.png)

### Post Build

If there are any failures, send an email.  If build passes, kick off the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature) job to merge the dev changes back to all feature branches.

![Cumulus_dev_cinnamon_deploy - Post Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-post_build.png)
