# CumulusCI Introduction

## Overview

This document provides a high level introduction to the Cumulus Continuous Integration infrastructure (CumulusCI).  CumulusCI is the process used by the Salesforce.com Foundation for the Cumulus project, the next generation of the Non-Profit Starter Pack (NPSP).

The process integrates GitHub, Jenkins, the Salesforce.com Ant Migration Tool, and a custom web application called mrbelvedere running on Heroku.

The following diagram provides a visual representation of the process flow for our internal dev team:

![CumulusCI Workflow](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/cumulus_ci_workflow.png)

The diagram uses multiple colors to represent different sections of the process:

* Feature Branch Process
* Dev Branch Process
* UAT Process
* Production Release Process

While this process was specifically built for the Cumulus project, it should be useable by other projects as well.

## About Cumulus

Project Cumulus is an update and overhaul of the existing Salesforce.com Foundation Nonprofit Starterpack.  More detail about the project is available through the [Cumulus](https://github.com/SalesforceFoundation/Cumulus) GitHub repository, however there are some details useful to explaining the CumulusCI process:

* Cumulus depends on 5 other managed packages each with a large install base.  Feature branches often require new versions of one of the underlying package.
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

## Feature Branch Process

All development work for Cumulus is done in feature branches with a naming convention of `feature/123-description-of-feature' where 123 is the GitHub issue number associated with the branch and description-of-feature is a short description of what the branch contains.

Whenever a new feature branch is pushed to the repository in GitHub or when a push is made against an existing feature branch, the [mrbelvedere](https://github.com/SalesforceFoundation/CumulusCI/blob/docs/mrbelvedere) Heroku app triggers the Cumulus_feature job to build the branch and report any build failures to the developer who last committed to the branch.  It also marks build status of the commit via the [GitHub Commit Status API](https://github.com/blog/1227-commit-status-api) so any Pull Requests created from the feature branch are marked with their build status as shown in the two examples below:

![GitHub Commit Status Passing](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-commit_status_error.png)

![GitHub Commit Status Passing](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-commit_status_pass.png)

Once a feature branch's Pull Request is approved and merged into the `dev` branch, the Dev Branch Process starts to test the merged code.

### Keeping feature branches in sync with dev

One challenge of a feature branch approach is how to keep feature branches in sync with the dev branch.  For example, say I start on a feature branch, feature/1-some-feature.  At the same time, another developer starts the feature/2-another-feature branch.  The other developer completes their branch before I do and submits a Pull Request which is approved and merged into dev.  At this point, my feature/1-some-feature branch is out of sync with dev.

The typical process to handle this example would be for the developer to merge the changes from dev back into their branch.  However, there is not an easy way for them to know this needs to be done.  If dev is not merged into their branch, then a build run on their feature branch does not accurately reflect how their code would function when merged with `dev`.

To handle this use case, we use the Cumulus_dev_to_feature job at the end of the Dev Branch Process to push all changes to dev which have passed all builds back into all open feature branches.  This way, the next time the developer goes to push from their local repository to their feature branch on GitHub, they will be notified that there are new changes they need to pull to their local branch.  This is usually as simple as running `git pull`.

## Dev Branch Process

The `dev` branch is the only persistent branch in the process and should always be passing builds.  We test all feature branches before merge and all feature branches are kept up to date with any changes to the `dev` branch.

There is a 4 step chain of builds involved in the Dev Branch Process:

1. [Cumulus_dev](https://github.com/SalesforceFoundation/CumulusCI): This job triggers after any commit to the `dev` branch and uses the deployCI ant target to clean the cumulus.dev org, upgrade any managed package versions which need upgraded, and deploys the `dev` branch code to the org running all apex tests.  If the build passes, the Cumulus_dev_cinnamon_deploy job is run.  If the build fails, all developers are notified.
2. Cumulus_dev_cinnamon_deploy: This job deploys the `dev` branch code to the dedicated org (cumulus.dev.cin) for running Cinnamon browser based tests (Selenium + SauceLabs).  This job only deploys the Cumulus code to the org and does not kick off the Cinnamon tests.  If the build passes, the Cumulus_dev_cinnamon_test job is run.
3. Cumulus_dev_cinnamon_test: This job deploys the [CumulusTesting](https://github.com/SalesforceFoundation/CumulusTesting) repository containing the Cinnamon tests for Cumulus to the cumulus.dev.cin target org and then kicks off the Cinnamon tests.  It parses the test results as a JUnit report so it can show individual test failure trends.  If all tests pass, it then runs the Cumulus_dev_to_feature job
4. Cumulus_dev_to_feature: This job pushes all changes from the `dev` branch to all feature branches.  If a merge conflict is encountered, it creates a Pull Request in GitHub to merge dev into the feature branch.  Once the developer manually resolves the merge conflict, the Pull Request is closed automatically.

## UAT Process

The Cumulus team works on a Scrum process with 2 week development iterations.  At the end of each iteration, managed beta package is built for User Acceptance Testing (UAT).  The purpose of the UAT process is to identify issues which prevent the release from going into production.  Changes in functionality which are merely enhancements on the release's functionality should be handled through the normal development process.

### Building a UAT Release

Creating a UAT release is a 3 step process requiring manual interaction with GitHub and the package org.

#### Step 1: Creating the release in GitHub

GitHub has support for managing Releases with a repository.  A release in GitHub is simply a git tag with addional metadata including a markdown enabled body field.

When the `dev` branch is ready to be rolled over into a UAT release, a Release is created in GitHub by going to the repository, clicking the Releases tab, and clicking the *Draft a new release* button.

UAT releases should have the *This is a pre-release* checkbox checked and should use the naming conventions `uat/1.0-beta2` for the tag name and `1.0 (Beta 2)` for the release name.  The release name syntax should exactly model the Force.com version number for the managed beta version which will contain it.

![Github - Creating a UAT Release](https://raw.github.com/SalesforceFoundation/CumulusCI/master/docs/github-creating_a_uat_release.png)

Once the release is published, mrbelvedere kicks off the Cumulus_uat job to deploy the tag's code to the packing org (cumulus.rel) so a beta managed package can be created.

#### Step 2: Creating the beta managed package

Once the Cumulus_uat build passes, the code should be deployed to the packaging org.  To create the beta managed package:

* go to Setup -> Create -> Packages and select the Cumulus package.  
* Use the Add Component button to add all the components to the package.
* Use the Upload button to create a new Beta Managed Package version.
* When you receive the email that the package is available, copy the install url

#### Step 3: Add Install URL to GitHub Release

Once the beta managed package is ready, we need to update the body of the GitHub release created in Step 1 to include the install URL for the package.  

The mrbelvedere app looks for an installation URL in the body of the Release when searching for the latest beta release.  This is necessary since the Release's tag must be created in the repository, tested, and finally manually packaged before the package can be installed in an org.  Adding the URL to the body of the Release is essentially a way to flag the release as ready.  GitHub Releases have a draft mode but the draft mode does not create a tag in the repository until it is published and thus does not solve this issue.

### Testing the UAT Release

The Cumulus_uat_managed job in Jenkins monitors the mrbelvedere app for a change in the latest managed beta package version.  When a change is detected, a build is triggered to deploy the managed package to the cumulus.uat org and then kick off all tests in the org.

## Production Release Process

Coming soon...
