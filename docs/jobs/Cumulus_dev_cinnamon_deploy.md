# Job: Cumulus_dev_cinnamon_deploy
[See it in action](http://ci.salesforcefoundation.org/view/dev)

## Overview

This job is responsible for deploying the dev branch to the dedicated org for running Cinnamon tests against the dev branch.  Once the deployment completes, it kicks off the Cumulus_dev_cinnamon_test job to actually run the Cinnamon tests.

Cinnamon is a framework for using Apex to execute Selenium browser based tests for UI functionality which can't be fully tested via Apex.  The Salesforce.com Foundation is a pilot user of the new framework.  Thus, these instructions are not portable to other projects at this point in time but are documented here for future use if/when the package is available.

## Target Org

Since Cinnamon requires the installation of additional managed packages not required by Cumulus, we use a dedicated org to run the Cinnamon tests.  We refer to this org as cumulus.dev.cin

## Configuration

### Source Code Management

We want to deploy the `dev` branch of the main Cumulus repository.

### Triggers

This job is triggered by any commit to the `dev` branch

### Build

We use the deployCI target to do a complete clean, update, deploy, and test of Cumulus.

### Post Build

If there are any failures, send an email to the release manager to investigate.  Send another email when a failing build passes again.

If the build succeeds, kick off the [Cumulus_dev_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_test.md) job to run the Cinnamon tests.

![Cumulus_dev_cinnamon_deploy - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_dev_cinnamon_deploy.png)
