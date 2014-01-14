# Job: Cumulus_dev_cinnamon_test

## Overview

This job runs after the [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md) job has passed build.  It is responsible for deploying the Cinnamon tests from the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository and executing the tests.  It reads the test results in JUnit report format to produce a graph of test execution status.

If the job passes build, it kicks off the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature) job.

## Target Org

This job runs against the cumulus.dev.cin org which is dedicated to running Cinnamon test against the dev branch.

## Configuration

### Source Code Management

### Build Environment

### Triggers

### Build

### Post Build

* The Editable Email Notification post build action is used to send a formatted email to dev team

![Cumulus_dev_cinnamon_test - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_dev_cinnamon_test.png)
