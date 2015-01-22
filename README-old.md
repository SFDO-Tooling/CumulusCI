# CumulusCI Introduction
[See it in action](http://ci.salesforcefoundation.org)

## Contents

* [Overview](#overview)
* [About Cumulus](#about-cumulus)
* [Repository Workflow](#repository-workflow)
  * [Merge vs Rebase](#merge-vs-rebase)
  * [External Contributions](#external-contributions)
* [Build Targets](#build-targets)
* [Feature Branch Process](#feature-branch-process)
* [Dev Branch Process](#dev-branch-process)
* [UAT Process](#uat-process)
* [Production Release Process](#production-release-process)
* [Installation and Setup](#installation-and-setup)


## Overview

[![CumulusCI Workflow](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/cumulus_ci_workflow.png)](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/cumulus_ci_workflow.png)

This document provides a high level introduction to the Cumulus Continuous Integration infrastructure (CumulusCI).  CumulusCI is the process used by the Salesforce.com Foundation for the Cumulus project, the next generation of the Non-Profit Starter Pack (NPSP).

The process integrates GitHub, Jenkins, the Salesforce.com Ant Migration Tool, and a custom web application called [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) running on Heroku.

While this process was specifically built for the Cumulus project, it should be useable by other Force.com projects.

## About Cumulus

Project Cumulus is an update and overhaul of the existing Salesforce.com Foundation Nonprofit Starterpack.  More detail about the project is available through the [Cumulus](https://github.com/SalesforceFoundation/Cumulus) GitHub repository, however there are some details useful to explaining the CumulusCI process:

* Cumulus depends on 5 other managed packages each with a large install base.  Feature branches often require new versions of one of the underlying package.
* Cumulus will be released as a managed package.
* Our team uses a Scrum process where every story has a corresponding issue in GitHub.
* We need to address the workflow needs of our internal developers while also creating an open and transparent way for external developers to contribute.

## Repository Workflow

The CumulusCI process is a hybrid pulling concepts from GitHub Flow and Git Flow to adapt to the unique build requirements of doing CI on the Force.com platform.

There is only one main, persistent branch in the repository and it is named `dev` to avoid confusion of whether the ""master"" branch means the current development version or the current production version.  All other branches are created off `dev` and are designed to be deleted once merged back into dev.

All development work is done in feature branches.  Completed feature branches are merged into the `dev` branch via a GitHub Pull Request.  No commits should ever be made to the `dev` branch directly.

### Merge vs Rebase

Since the process is based heavily around GitHub Pull Requests which use `git merge` behind the scenes to perform the merge operation on approved Pull Requests, we have opted for a merge instead of rebase approach.  To ensure that history stays consistent, `git rebase` should never be used in the Cumulus repository.

### External Contributions

The workflow for the internal team uses a single repository owned by the SalesforceFoundation organization in GitHub.  The process for external contributors is slightly different.  Since external contributors do not have rights to the repository, they cannot create their own feature branches directly in the repository.  They need to first fork the repository in GitHub and then use the same process used by internal developers to build a feature branch.  Once the branch is ready, the external contribution is submitted as a GitHub Pull Request against the `dev` branch of the SalesforceFoundation/Cumulus repository.

#### Creating an External Contribution

1. Fork the Cumulus repository in GitHub
2. Create a new branch in your fork using the format feature/123-feature-description where 123 is a valid issue number from the main repository and feature-description is a brief description of the feature.
3. Make your changes and push to the feature branch in your fork.
4. Submit a Pull Request to merge your feature branch into the `dev` branch of the main Cumulus repository
5. If your feature branch is behind `dev`, mrbelvedere will comment on your Pull Request that you need to merge the dev changes back to your branch.  This can be done either with a Pull Request through the GitHub site or via a git merge in a local repository.
6. When your branch is not behind `dev`, mrbelvedere will ask if one of the admins can approve building the Pull Request.
7. When an admin approves the build, mrbelvedere will comment with a note that the build is queued along with a link to view the build status on Jenkins
8. When the build is complete, the Commit Status will be set on the Pull Request and mrbelvedere will comment on the Pull Request with the status so you can receive updates through GitHub.
9. When your pull request is approved for build, any additional commits you make against the feature branch will automatically trigger a new build allowing you to see the build results on any changes made per review comments.

## Build Targets

Cumulus uses a [build.xml](https://github.com/SalesforceFoundation/Cumulus/blob/dev/build.xml) file in the root of the repository to provide a number of useful Ant build targets for working on, deploying, and testing Cumulus.  Even without a deployed Jenkins server, these targets allow anyone to check out the repository and quickly deploy either an unmanaged or managed version of Cumulus to a DE or Partner DE org.

The following build targets are defined in the [build.xml](https://github.com/SalesforceFoundation/Cumulus/blob/dev/build.xml) file:

### deploy

Runs a simple deployment of the code including execution of all Apex tests as part of the deployment.  If any test failures occur, the deployment is rolled back.

### deployWithoutTest

Runs a simple deployment of the code but does not execute all Apex tests.  This is useful if you want to quickly deploy already tested code into an org.

### deployCI

Runs a complete clean, update, build, test cycle.  Starts with the [uninstallCumulus](#uninstallcumulus) target to clean unpackaged metadata from the org.  Then runs [updateDependentPackages](#updatedependentpackages) to ensure all managed packages match the required versions for the checked out code.  Finally, runs [deploy](#deploy) to deploy the code and run all tests.

NOTE: This is a very destructive operation which is designed to be run against organizations dedicated to CI purposes.  Do not run this against an org with any metadata you care about keeping.

### deployManagedUAT

Deploys the 5 NPSP managed packages plus the latest beta managed package for Cumulus.

Calls out to the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) application to get the latest beta managed package version and its corresponding repository tag.  Sets the required versions per the repository tag's version.properties file and then runs [updateDependentPackages](#updatedependentpackages) to do the install/uninstall of managed packages so they are the requested version.  Finally, calls [runAllTests](#runalltests) to kick off all the Apex tests deployed in the org.

### uninstallCumulus

Uninstalls all unpackaged metadata of types used by Cumulus from a target org.  First, reads all metadata from the org.  Next, builds and deploys a package to reset all ActionOverrides to default on Standard Objects (Account, Contact, Lead, and Opportunity).  Next, builds and deploys a package with a destructiveChanges.xml file to delete all unpackaged metadata which can be deleted.

### updateDependentPackages

Ensures that all 5 original NPSP packages (npe01, npo02, npe03, npe4, and npe5) and the Cumulus managed package (npsp) are installed and at the correct version.  If a package needs to be downgraded, it is first uninstalled.  If a package needs to be upgraded, the upgraded version is installed without first uninstalling the package.

### retrieveUnpackaged

Retrieves all unpackaged metadata from the org.  This target is more a utility for developers than a part of the CI process.

### runAllTests

Uses a blank package to deploy and then run all tests in the target org.  This is useful if the code you want to test is already deployed (i.e. from a managed package) and you just want to kick off the deployed tests.

## Feature Branch Process

* [Cumulus_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_feature.md): Runs a full build against an org dedicated to test feature branches.
* [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature.md): Pushes all changes from the `dev` branch to all feature branches.  If a merge conflict is encountered, it creates a Pull Request in GitHub to merge dev into the feature branch.  Once the developer manually resolves the merge conflict, the Pull Request is closed automatically.
* [Cumulus_check_dependent_versions](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_check_dependent_versions.md): Checks to make sure the `scripts/set_dependent_versions.py` script was run after changing the `scripts/cumulus.cfg` file.

All development work for Cumulus is done in feature branches with a naming convention of `feature/123-description-of-feature' where 123 is the GitHub issue number associated with the branch and description-of-feature is a short description of what the branch contains.

Whenever a new feature branch is pushed to the repository in GitHub or when a push is made against an existing feature branch, the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) Heroku app triggers the [Cumulus_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_feature.md) job to build the branch and report any build failures to the developer who last committed to the branch.  It also marks build status of the commit via the [GitHub Commit Status API](https://github.com/blog/1227-commit-status-api) so any Pull Requests created from the feature branch are marked with their build status as shown in the two examples below:

![GitHub Commit Status Failing](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-commit_status_error.png)

![GitHub Commit Status Passing](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-commit_status_pass.png)

Once a feature branch's Pull Request is approved and merged into the `dev` branch, the Dev Branch Process starts to test the merged code.

### Keeping feature branches in sync with dev

One challenge of a feature branch approach is how to keep feature branches in sync with the dev branch.  For example, say I start on a feature branch, feature/1-some-feature.  At the same time, another developer starts the feature/2-another-feature branch.  The other developer completes their branch before I do and submits a Pull Request which is approved and merged into dev.  At this point, my feature/1-some-feature branch is out of sync with dev.

The typical process to handle this example would be for the developer to merge the changes from dev back into their branch.  However, there is not an easy way for them to know this needs to be done.  If dev is not merged into their branch, then a build run on their feature branch does not accurately reflect how their code would function when merged with `dev`.

To handle this use case, we use the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature.md) job at the end of the Dev Branch Process to push all changes to dev which have passed build back into all open feature branches.  This way, the next time the developer goes to push from their local repository to their feature branch on GitHub, they will be notified that there are new changes they need to pull to their local branch.  This is usually as simple as running `git pull`.

## Dev Branch Process

The `dev` branch is the only persistent branch in the process and should always be passing builds.  We test all feature branches before merge and all feature branches are kept up to date with any changes to the `dev` branch.

There is a 3 step chain of builds involved in the Dev Branch Process:

1. [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev.md): This job triggers after any commit to the `dev` branch and uses the deployCI ant target to clean the cumulus.dev org, upgrade any managed package versions which need upgraded, and deploys the `dev` branch code to the org running all apex tests.  If all tests pass, it then runs the [Cumulus_dev_to_feature](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_to_feature.md) job.  If the build fails, all developers are notified.
2. [Cumulus_dev_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_deploy.md): This job deploys the `dev` branch code to the dedicated org (cumulus.dev.cin) for running Cinnamon browser based tests (Selenium + SauceLabs).  This job only deploys the Cumulus code to the org and does not kick off the Cinnamon tests.  If the build passes, the [Cumulus_dev_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_test.md) job is run.
3. [Cumulus_dev_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_dev_cinnamon_test.md): This job deploys the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository containing the Cinnamon tests for Cumulus to the cumulus.dev.cin target org and then kicks off the Cinnamon tests.  It parses the test results as a JUnit report so it can show individual test failure trends.

## UAT Process

The Cumulus team works on a Scrum process with 2 week development iterations.  At the end of each iteration, managed beta package is built for User Acceptance Testing (UAT).  The purpose of the UAT process is to identify issues which prevent the release from going into production.  Changes in functionality which are merely enhancements on the release's functionality should be handled through the normal development process.

The following Jenkins job handle the automation of the UAT Process to the extent currently possible on the Force.com platform.

* [Cumulus_uat](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat.md)
* [Cumulus_uat_cinnamon_deploy](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_deploy.md)
* [Cumulus_uat_cinnamon_test](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_cinnamon_test.md)
* [Cumulus_uat_managed](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_managed.md)

### Building a UAT Release

Creating a UAT release is a 3 step process requiring manual interaction with GitHub and the package org.

#### Step 1: Creating the release in GitHub

GitHub has support for managing Releases with a repository.  A release in GitHub is simply a git tag with addional metadata including a markdown enabled body field.

When the `dev` branch is ready to be rolled over into a UAT release, a Release is created in GitHub by going to the repository, clicking the Releases tab, and clicking the *Draft a new release* button.

UAT releases should have the *This is a pre-release* checkbox checked and should use the naming conventions `uat/1.0-beta2` for the tag name and `1.0 (Beta 2)` for the release name.  The release name syntax should exactly model the Force.com version number for the managed beta version which will contain it.

![Github - Creating a UAT Release](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-creating_a_uat_release.png)

Once the release is published, [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) kicks off the [Cumulus_uat](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat.md) job to deploy the tag's code to the packing org (cumulus.rel) so a beta managed package can be created.

#### Step 2: Creating the beta managed package

Once the [Cumulus_uat](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat.md) build passes, the code should be deployed to the packaging org.  To create the beta managed package:

* go to Setup -> Create -> Packages and select the Cumulus package.  
* Use the Add Component button to add all the components to the package.
* Use the Upload button to create a new Beta Managed Package version.
* When you receive the email that the package is available, copy the install url

#### Step 3: Add Install URL to GitHub Release

Once the beta managed package is ready, we need to update the body of the GitHub release created in Step 1 to include the install URL for the package.  

The [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) app looks for an installation URL in the body of the Release when searching for the latest beta release.  This is necessary since the Release's tag must be created in the repository, tested, and finally manually packaged before the package can be installed in an org.  Adding the URL to the body of the Release is essentially a way to flag the release as ready.  GitHub Releases have a draft mode but the draft mode does not create a tag in the repository until it is published and thus does not solve this issue.

### Testing the UAT Release

The [Cumulus_uat_managed](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_uat_managed.md) job in Jenkins monitors the [mrbelvedere](http://salesforcefoundation.github.io/mrbelvedere) app for a change in the latest managed beta package version.  When a change is detected, a build is triggered to deploy the managed package to the cumulus.uat org and then kick off all tests in the org.

## Production Release Process

[Cumulus_rel](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/jobs/Cumulus_rel.md)

More on the Release Process coming soon...

## Installation and Setup

The [Installation and Setup](https://github.com/SalesforceFoundation/CumulusCI/blob/master/docs/setup/README.md) documentation provides details on building out a server with Jenkins and the necessary plugins and configuration needed to run the jobs for CumulusCI.
