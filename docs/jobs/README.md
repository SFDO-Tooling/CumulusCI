# Cumulus CI - Jenkins Job Configuration

This document provides detailed instructions for configuring the jobs in Jenkins needed to support the Cumulus CI process.  It is assumed you have already completed the steps in the [Jenkins Installation and Setup documentation](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/setup/README.md) and thus have a server with Jenkins installed and configured with all needed plugins.

# Target Orgs

The Cumulus CI process uses a number of target orgs which can be Developer Edition or Partner Developer Edition instances.  With the exception of the orgs used for packaging (cumulus.rel) and orgs for cinnamon testing (cumulus.dev.cin and cumulus.uat.cin), all orgs used require no configuration beyond creating a build.properties file with the credentials Jenkins should use when deploying to the org.

## Configuring the cumulus.rel org

The cumulus.rel org is the packaging org for the Cumulus managed package.  This org is used to create both the UAT beta managed release versions and the production managed releases.  The org needs to be manually configured to build managed packages following the steps in [Creating Managed Packages](https://help.salesforce.com/HTViewHelpDoc?id=enabling_managed_packages.htm&language=en_US).

## Configuring the cumulus.dev.cin and cumulus.uat.cin orgs

These orgs are dedicated to running the Cinnamon browser based UI tests.  At the moment, we do not have an automated process for setting up the Cinnamon infrastruture in the org.  Thus, we have to do some manual configuration of these orgs before they can be plugged into the Jenkins jobs:

1. Install ApexSelenese
2. Install taaas (Cinnamon)
3. Go to Apps -> Cinnamon -> Setup (tab)
4. Fill in Saucelabs username and access key
5. Click the button *Connect to Your Org Under Test*
6. Set the Test Class Name Prefix to *Should*
7. Ensure the Remote Site Setting *self* refers to the correct pod for the instance (i.e. https://na15.salesforce.com if your instance is on na15)

## Creating build.properties files

The Cumulus repository contains a build.xml file in the root of the repository which can run multiple deployment scenarios (ant targets) against a target org.  The build.xml file requires a build.properties file to be passed via the *-propertyfile* command line argument.  The build.properties file should contain the following lines:

    sf.username = mrbelvedere@cumulus.dev
	sf.password = PASS+TOKEN
	sf.serverurl=https://login.salesforce.com

The job configurations below assume that each org used in the development process has a build.properties file under /var/lib/jenkins/workspace.  As a convention, we use the filename to signify the org whose credentials they contain such as build.properties.cumulus.dev for the org used by the cumulus.dev org.  When creating user logins in the org, we also use the naming format USERNAME@org.  For example, the username used by Jenkins for the cumulus.dev org is mrbelvedere@cumulus.dev.

# Jobs

## Development Jobs

* [Cumulus_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_feature.md): Tests feature branches
* [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev.md): Tests the dev branch
* [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md): Deploys dev branch for Cinnamon browser based tests
* [Cumulus_dev_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_test.md): Runs Cinnamon browser based tests
* [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature.md): Merges dev changes to open feature branches
* [Cumulus_dev_check_dependent_versions](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_check_dependent_versions.md): Sets version references for managed packages

## User Acceptance Testing (UAT) Jobs

* [Cumulus_uat](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat.md)
* [Cumulus_uat_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_deploy.md)
* [Cumulus_uat_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_test.md)
* [Cumulus_uat_managed](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_managed.md)

## Release Jobs

* [Cumulus_rel](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_rel.md)
