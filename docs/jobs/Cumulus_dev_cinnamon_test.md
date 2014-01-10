# Job: Cumulus_dev_cinnamon_test

## Overview

This job runs after the [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md) job has passed build.  It is responsible for deploying the Cinnamon tests from the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository and executing the tests.  It reads the test results in JUnit report format to produce a graph of test execution status.

If the job passes build, it kicks off the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature) job.

## Target Org

This job runs against the cumulus.dev.cin org which is dedicated to running Cinnamon test against the dev branch.

## Configuration

### Title and Description

![Cumulus_dev_cinnamon_test - Title and Description](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-title.png)

### Source Code Management

![Cumulus_dev_cinnamon_test - SCM](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-scm.png)

### Build Environment

![Cumulus_dev_cinnamon_test - Build Environment](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-build_environment.png)

### Triggers

![Cumulus_dev_cinnamon_test - Triggers](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-triggers.png)

### Build

![Cumulus_dev_cinnamon_test - Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-build.png)

### Post Build

This job takes 4 post build actions:

* The Editable Email Notification post build action is used to send a formatted email to dev team
* The *Set build status on GitHub commit* post build action flags the GitHub commit with the build status so the Branches list and Pull Requests for the branch show the build status with a link to the build job for more details.

![Cumulus_dev_cinnamon_test - Post Build](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/cumulus_dev_cinnamon_test-post_build.png)
