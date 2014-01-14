# Job: Cumulus_dev_cinnamon_test
[See it in action](http://ci.salesforcefoundation.org/view/dev)

## Overview

This job runs after the [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md) job has passed build.  It is responsible for deploying the Cinnamon tests from the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository and executing the tests.  It reads the test results in JUnit report format to produce a graph of test execution status.

If the job passes build, it kicks off the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature) job.

## Target Org

This job runs against the cumulus.dev.cin org which is dedicated to running Cinnamon test against the dev branch.

## Configuration

### Source Code Management

We point to the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository and deploy the `master` branch.

### Build Triggers

This build is triggered by the [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md)

The build is also triggered by any commits to the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository.

### Build Environment

We set the environment variables `USERNAME` and `PASSWORD` for the target org.  PASSWORD should contain the password and security token if needed to connect to the org.

### Build

The build for this job uses the default target in the build.xml of the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository.

After ant completes, a script is run to call the ccli client and run the Cinnamon tests.

### Post Build

The Cinnamon cli outputs a JUnit format report as output.xml.  We want to publish the test results so we get test trends for the job over time.

The Editable Email Notification post build action is used to send a formatted email to all developers on failure (Failure) and recovery (Fixed).

![Cumulus_dev_cinnamon_test - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_dev_cinnamon_test.png)
