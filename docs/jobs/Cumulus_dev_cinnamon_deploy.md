# Job: Cumulus_dev_cinnamon_deploy

## Overview

When the [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/jobs/Cumulus_dev.md) job completes, it kicks off Cumulus_dev_cinnamon_deploy.  This job is responsible for deploying the dev branch to the dedicated org for running Cinnamon tests against the dev branch.  Once the deployment completes, it kicks off the Cumulus_dev_cinnamon_test job to actually run the Cinnamon tests.

Cinnamon is a framework for using Apex to execute Selenium browser based tests for UI functionality which can't be fully tested via Apex.  The Salesforce.com Foundation is a pilot user of the new framework.  Thus, these instructions are not portable to other projects at this point in time but are documented here for future use if/when the package is available.

## Target Org

Since Cinnamon requires the installation of additional managed packages not required by Cumulus, we use a dedicated org to run the Cinnamon tests.  We refer to this org as cumulus.dev.cin

## Configuration

### Title and Description

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-title.png)

### Source Code Management

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-scm.png)

### Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-build.png)

### Post Build

![Jenkins Settings - Location](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_deploy-post_build.png)
