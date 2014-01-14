# Job: Cumulus_uat_cinnamon_test
[See it in action](http://ci.salesforcefoundation.org/view/uat)

## Overview

The Cumulus_uat_cinnamon_test is the second job of two involved in executing browser based tests through SauceLabs using Cinnamon.  This job is responsible for deploying the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository, a Force.com package containing the Cinnamon tests.  After the tests are deployed to the cumulus.uat.cin org, the Cinnamon command line client is used to kick off tests.


the  the [Cumulus_uat_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_test.md) build to run the Cinnamon tests.

## Target Org

This job runs against the dedicated cumulus.dev.cin org which has Cinnamon installed and configured manually outside of the build process.

## Configuration

### Source Code Management

We point to the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository and deploy the `master` branch.

### Build Triggers

This build is triggered by the [Cumulus_uat_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_deploy.md)

### Build Environment

We set the environment variables `USERNAME` and `PASSWORD` for the target org.  PASSWORD should contain the password and security token if needed to connect to the org.

### Build

The build for this job uses the default target in the build.xml of the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository.

After ant completes, a script is run to call the ccli client and run the Cinnamon tests.

### Post Build

The Cinnamon cli outputs a JUnit format report as output.xml.  We want to publish the test results so we get test trends for the job over time.

The Editable Email Notification post build action is used to send a formatted email to the developer who created the tag if the build fails (Failure) or recovers from a failure (Fixed).

The *Set build status on GitHub commit* post build action flags the GitHub commit.

![Cumulus_uat_cinnamon_test - Config](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/jobs/Cumulus_uat_cinnamon_test.png)
